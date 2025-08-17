from django import forms
from .models import OperatorProcessCapacityScore

class GenerateScoringReportForm(forms.Form):
    """生成評分報表表單"""
    company_code = forms.CharField(
        max_length=10,
        label="公司代號",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        label="開始日期",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        label="結束日期",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    report_period = forms.ChoiceField(
        choices=[
            ('daily', '日報'),
            ('weekly', '週報'),
            ('monthly', '月報'),
            ('quarterly', '季報'),
        ],
        label="報表週期",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class SupervisorScoreForm(forms.ModelForm):
    """主管評分表單"""
    class Meta:
        model = OperatorProcessCapacityScore
        fields = ['supervisor_score', 'supervisor_comment']
        widgets = {
            'supervisor_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '0.1',
                'placeholder': '請輸入0-100的分數'
            }),
            'supervisor_comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '請輸入評語（可選）'
            }),
        }
    
    def clean_supervisor_score(self):
        """驗證主管評分"""
        score = self.cleaned_data.get('supervisor_score')
        if score is not None:
            if score < 0 or score > 100:
                raise forms.ValidationError('主管評分必須在0-100之間')
        return score

class OperatorScoreFilterForm(forms.Form):
    """作業員評分篩選表單"""
    company_code = forms.CharField(
        max_length=10,
        label="公司代號",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    operator_id = forms.CharField(
        max_length=50,
        label="作業員編號",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    process_name = forms.CharField(
        max_length=100,
        label="工序名稱",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        label="開始日期",
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        label="結束日期",
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    has_supervisor_score = forms.ChoiceField(
        choices=[
            ('', '全部'),
            ('yes', '已評分'),
            ('no', '未評分'),
        ],
        label="主管評分狀態",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    ) 