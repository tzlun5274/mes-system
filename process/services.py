"""
工序管理服務層
封裝複雜的業務邏輯，處理作業員與技能管理相關的服務
"""

from django.contrib import messages
from .models import Operator, OperatorSkill, ProcessName
from production.models import ProductionLine


class OperatorService:
    """作業員管理服務"""
    
    @staticmethod
    def create_operator_with_skills(name, production_line_id, process_name_ids, priorities):
        """
        建立作業員並設定技能
        
        參數:
            name: 作業員名稱
            production_line_id: 產線ID
            process_name_ids: 工序名稱ID列表
            priorities: 優先順序列表
            
        回傳:
            tuple: (operator, error_message)
        """
        try:
            # 檢查作業員名稱是否已存在
            if Operator.objects.filter(name=name).exists():
                return None, f"作業員名稱 '{name}' 已存在，請選擇其他名稱！"
            
            # 透過API查詢產線資訊
            production_line_name = ""
            if production_line_id:
                try:
                    production_line = ProductionLine.objects.filter(id=production_line_id).first()
                    if production_line:
                        production_line_name = production_line.line_name
                except:
                    pass
            
            # 建立作業員
            operator = Operator(
                name=name,
                production_line_id=production_line_id,
                production_line_name=production_line_name
            )
            operator.save()
            
            # 驗證工序和優先順序數量匹配
            if len(process_name_ids) != len(priorities):
                operator.delete()
                return None, "工序名稱和優先順序數量不匹配！"
            
            # 建立技能記錄
            for process_name_id, priority in zip(process_name_ids, priorities):
                if process_name_id and priority:
                    try:
                        priority = int(priority)
                        if priority < 1:
                            operator.delete()
                            return None, "技能優先順序必須是正整數！"
                        
                        process_name = ProcessName.objects.get(id=process_name_id)
                        OperatorSkill.objects.create(
                            operator_id=str(operator.id),
                            operator_name=operator.name,
                            process_name_id=str(process_name.id),
                            process_name=process_name.name,
                            priority=priority
                        )
                    except (ValueError, ProcessName.DoesNotExist):
                        operator.delete()
                        return None, "無效的工序或優先順序數據！"
            
            return operator, None
            
        except Exception as e:
            return None, f"建立作業員時發生錯誤：{str(e)}"
    
    @staticmethod
    def update_operator_with_skills(operator, new_name, production_line_id, process_name_ids, priorities, skill_ids):
        """
        更新作業員資訊和技能
        
        參數:
            operator: Operator 物件
            new_name: 新名稱
            production_line_id: 產線ID
            process_name_ids: 工序名稱ID列表
            priorities: 優先順序列表
            skill_ids: 技能ID列表
            
        回傳:
            tuple: (success, error_message)
        """
        try:
            # 檢查名稱是否重複
            if new_name != operator.name and Operator.objects.filter(name=new_name).exists():
                return False, f"作業員名稱 '{new_name}' 已存在，請選擇其他名稱！"
            
            # 更新基本資訊
            operator.name = new_name
            
            # 透過API查詢產線資訊
            production_line_name = ""
            if production_line_id:
                try:
                    production_line = ProductionLine.objects.filter(id=production_line_id).first()
                    if production_line:
                        production_line_name = production_line.line_name
                except:
                    pass
            
            operator.production_line_id = production_line_id
            operator.production_line_name = production_line_name
            operator.save()
            
            # 驗證工序和優先順序數量匹配
            if len(process_name_ids) != len(priorities):
                return False, "工序名稱和優先順序數量不匹配！"
            
            # 刪除未提交的技能
            submitted_skill_ids = [int(sid) for sid in skill_ids if sid]
            existing_skills = OperatorSkill.objects.filter(operator_id=str(operator.id)).exclude(
                id__in=submitted_skill_ids
            )
            for skill in existing_skills:
                skill.delete()
            
            # 更新或建立技能
            for i, (process_name_id, priority) in enumerate(zip(process_name_ids, priorities)):
                if process_name_id and priority:
                    try:
                        priority = int(priority)
                        if priority < 1:
                            return False, "技能優先順序必須是正整數！"
                        
                        process_name = ProcessName.objects.get(id=process_name_id)
                        if i < len(skill_ids) and skill_ids[i]:
                            # 更新現有技能
                            skill = OperatorSkill.objects.get(id=skill_ids[i])
                            skill.process_name_id = str(process_name.id)
                            skill.process_name = process_name.name
                            skill.priority = priority
                            skill.save()
                        else:
                            # 建立新技能
                            OperatorSkill.objects.create(
                                operator_id=str(operator.id),
                                operator_name=operator.name,
                                process_name_id=str(process_name.id),
                                process_name=process_name.name,
                                priority=priority,
                            )
                    except (ValueError, ProcessName.DoesNotExist):
                        return False, "無效的工序或優先順序數據！"
            
            return True, None
            
        except Exception as e:
            return False, f"更新作業員時發生錯誤：{str(e)}"


class OperatorStatisticsService:
    """作業員統計服務"""
    
    @staticmethod
    def get_operator_statistics():
        """
        取得作業員統計資料
        
        回傳:
            dict: 包含各種統計資料的字典
        """
        from django.utils import timezone
        
        today = timezone.now().date()
        
        return {
            'total_operators': Operator.objects.count(),
            'skilled_operators_count': OperatorSkill.objects.values('operator_id').distinct().count(),
            'high_priority_skills_count': OperatorSkill.objects.filter(priority=1).count(),
            'today_new_operators_count': 0,  # Operator 模型沒有 created_at 欄位
        }


class OperatorImportExportService:
    """作業員匯入匯出服務"""
    
    @staticmethod
    def get_operator_skills_for_export():
        """
        取得用於匯出的作業員技能資料
        
        回傳:
            QuerySet: OperatorSkill 查詢集
        """
        return OperatorSkill.objects.all()
    
    @staticmethod
    def import_operator_skill_data(dataset, overwrite=False):
        """
        匯入作業員技能資料
        
        參數:
            dataset: 資料集
            overwrite: 是否覆蓋現有資料
            
        回傳:
            tuple: (success_count, error_messages)
        """
        success_count = 0
        error_messages = []
        
        for row in dataset:
            try:
                operator_name = row["作業員名稱"]
                production_line_name = row.get("所屬單位", "")
                process_name = row["工序名稱"]
                priority = row["技能優先順序"]
                
                if not operator_name or not process_name:
                    continue
                
                # 取得工序
                try:
                    process = ProcessName.objects.get(name=process_name)
                except ProcessName.DoesNotExist:
                    error_messages.append(f"找不到工序：{process_name}")
                    continue
                
                # 處理優先順序
                try:
                    priority = int(priority) if priority else 1
                except (ValueError, TypeError):
                    priority = 1
                
                # 透過API查詢產線資訊
                production_line = None
                if production_line_name:
                    try:
                        production_line = ProductionLine.objects.get(line_name=production_line_name)
                    except ProductionLine.DoesNotExist:
                        error_messages.append(f"找不到產線：{production_line_name}")
                
                # 建立或取得作業員
                operator, created = Operator.objects.get_or_create(name=operator_name)
                
                # 更新作業員的產線資訊
                if production_line:
                    operator.production_line_id = str(production_line.id)
                    operator.production_line_name = production_line.line_name
                    operator.save()
                
                # 建立或更新技能
                existing_skill = OperatorSkill.objects.filter(
                    operator_id=str(operator.id), process_name_id=str(process.id)
                ).first()
                
                if existing_skill:
                    if overwrite:
                        existing_skill.priority = priority
                        existing_skill.save()
                else:
                    OperatorSkill.objects.create(
                        operator_id=str(operator.id),
                        operator_name=operator.name,
                        process_name_id=str(process.id),
                        process_name=process.name,
                        priority=priority
                    )
                
                success_count += 1
                
            except Exception as e:
                error_messages.append(f"處理資料時發生錯誤：{str(e)}")
        
        return success_count, error_messages
