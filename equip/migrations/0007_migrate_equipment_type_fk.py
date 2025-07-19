# 自動產生：將舊設備類型字串搬移到新外鍵欄位
from django.db import migrations


def migrate_equipment_type_fk(apps, schema_editor):
    Equipment = apps.get_model("equip", "Equipment")
    EquipmentType = apps.get_model("equip", "EquipmentType")
    type_map = {
        "smt": "SMT 設備",
        "test": "測試設備",
        "inspection": "檢測設備",
        "assembly": "組裝設備",
        "packaging": "包裝設備",
        "other": "其他設備",
    }
    for eq in Equipment.objects.all():
        type_name = type_map.get(eq.equipment_type, "其他設備")
        eq_type = EquipmentType.objects.filter(name=type_name).first()
        eq.equipment_type_fk = eq_type
        eq.save()


def reverse_equipment_type_fk(apps, schema_editor):
    Equipment = apps.get_model("equip", "Equipment")
    for eq in Equipment.objects.all():
        eq.equipment_type_fk = None
        eq.save()


class Migration(migrations.Migration):
    dependencies = [
        ("equip", "0006_equipmenttype_alter_equipment_equipment_type_and_more"),
    ]
    operations = [
        migrations.RunPython(migrate_equipment_type_fk, reverse_equipment_type_fk),
    ]
