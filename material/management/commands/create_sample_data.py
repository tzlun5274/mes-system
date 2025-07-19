# material/management/commands/create_sample_data.py
# 這個檔案建立測試資料，包含物料、產品、BOM、庫存等資料，方便測試物料需求估算功能。

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from material.models import Material, Product, BOM, MaterialInventory, Order


class Command(BaseCommand):
    help = "建立物料管理模組的測試資料"

    def handle(self, *args, **options):
        self.stdout.write("開始建立測試資料...")

        # 建立物料
        materials = []
        material_data = [
            {
                "code": "MAT001",
                "name": "電阻 10KΩ",
                "category": "被動元件",
                "supplier": "供應商A",
            },
            {
                "code": "MAT002",
                "name": "電容 100μF",
                "category": "被動元件",
                "supplier": "供應商A",
            },
            {
                "code": "MAT003",
                "name": "IC 8051",
                "category": "主動元件",
                "supplier": "供應商B",
            },
            {
                "code": "MAT004",
                "name": "PCB 基板",
                "category": "基板",
                "supplier": "供應商C",
            },
            {
                "code": "MAT005",
                "name": "LED 紅光",
                "category": "光電元件",
                "supplier": "供應商D",
            },
        ]

        for data in material_data:
            material, created = Material.objects.get_or_create(
                material_code=data["code"],
                defaults={
                    "name": data["name"],
                    "category": data["category"],
                    "supplier": data["supplier"],
                    "specification": f'{data["name"]} 規格說明',
                    "lead_time_days": 7,
                    "min_order_quantity": 100,
                    "safety_stock": 50,
                },
            )
            materials.append(material)
            if created:
                self.stdout.write(
                    f"建立物料: {material.material_code} - {material.name}"
                )

        # 建立產品
        products = []
        product_data = [
            {"code": "PROD001", "name": "LED 控制板"},
            {"code": "PROD002", "name": "感測器模組"},
            {"code": "PROD003", "name": "通訊模組"},
        ]

        for data in product_data:
            product, created = Product.objects.get_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "description": f'{data["name"]} 產品描述',
                },
            )
            products.append(product)
            if created:
                self.stdout.write(f"建立產品: {product.code} - {product.name}")

        # 建立 BOM
        bom_data = [
            # LED 控制板 BOM
            {
                "product": "PROD001",
                "material": "MAT001",
                "quantity": 5,
                "position": "電路板",
            },
            {
                "product": "PROD001",
                "material": "MAT002",
                "quantity": 3,
                "position": "電路板",
            },
            {
                "product": "PROD001",
                "material": "MAT003",
                "quantity": 1,
                "position": "電路板",
                "critical": True,
            },
            {
                "product": "PROD001",
                "material": "MAT004",
                "quantity": 1,
                "position": "基板",
                "critical": True,
            },
            {
                "product": "PROD001",
                "material": "MAT005",
                "quantity": 10,
                "position": "顯示",
            },
            # 感測器模組 BOM
            {
                "product": "PROD002",
                "material": "MAT001",
                "quantity": 8,
                "position": "電路板",
            },
            {
                "product": "PROD002",
                "material": "MAT002",
                "quantity": 4,
                "position": "電路板",
            },
            {
                "product": "PROD002",
                "material": "MAT003",
                "quantity": 1,
                "position": "電路板",
                "critical": True,
            },
            {
                "product": "PROD002",
                "material": "MAT004",
                "quantity": 1,
                "position": "基板",
                "critical": True,
            },
            # 通訊模組 BOM
            {
                "product": "PROD003",
                "material": "MAT001",
                "quantity": 12,
                "position": "電路板",
            },
            {
                "product": "PROD003",
                "material": "MAT002",
                "quantity": 6,
                "position": "電路板",
            },
            {
                "product": "PROD003",
                "material": "MAT003",
                "quantity": 2,
                "position": "電路板",
                "critical": True,
            },
            {
                "product": "PROD003",
                "material": "MAT004",
                "quantity": 1,
                "position": "基板",
                "critical": True,
            },
        ]

        for data in bom_data:
            product = Product.objects.get(code=data["product"])
            material = Material.objects.get(material_code=data["material"])

            bom, created = BOM.objects.get_or_create(
                product=product,
                material=material,
                defaults={
                    "quantity": data["quantity"],
                    "position": data["position"],
                    "is_critical": data.get("critical", False),
                },
            )
            if created:
                self.stdout.write(
                    f'建立 BOM: {product.code} - {material.material_code} ({data["quantity"]}個)'
                )

        # 建立庫存
        inventory_data = [
            {"material": "MAT001", "quantity": 1000, "reserved": 200},
            {"material": "MAT002", "quantity": 800, "reserved": 150},
            {"material": "MAT003", "quantity": 50, "reserved": 10},
            {"material": "MAT004", "quantity": 200, "reserved": 50},
            {"material": "MAT005", "quantity": 500, "reserved": 100},
        ]

        for data in inventory_data:
            material = Material.objects.get(material_code=data["material"])
            inventory, created = MaterialInventory.objects.get_or_create(
                material=material,
                defaults={
                    "quantity": data["quantity"],
                    "reserved_quantity": data["reserved"],
                },
            )
            if created:
                self.stdout.write(
                    f'建立庫存: {material.material_code} ({data["quantity"]}個)'
                )

        # 建立訂單
        order_data = [
            {
                "product": "PROD001",
                "quantity": 100,
                "due_date": date.today() + timedelta(days=30),
            },
            {
                "product": "PROD002",
                "quantity": 50,
                "due_date": date.today() + timedelta(days=45),
            },
            {
                "product": "PROD003",
                "quantity": 75,
                "due_date": date.today() + timedelta(days=60),
            },
        ]

        for data in order_data:
            product = Product.objects.get(code=data["product"])
            order, created = Order.objects.get_or_create(
                product=product,
                quantity=data["quantity"],
                due_date=data["due_date"],
                defaults={"status": "pending"},
            )
            if created:
                self.stdout.write(f'建立訂單: {product.code} ({data["quantity"]}個)')

        self.stdout.write(self.style.SUCCESS("測試資料建立完成！"))
        self.stdout.write(f"已建立 {len(materials)} 個物料")
        self.stdout.write(f"已建立 {len(products)} 個產品")
        self.stdout.write(f"已建立 {len(bom_data)} 個 BOM 項目")
        self.stdout.write(f"已建立 {len(inventory_data)} 個庫存記錄")
        self.stdout.write(f"已建立 {len(order_data)} 個訂單")
