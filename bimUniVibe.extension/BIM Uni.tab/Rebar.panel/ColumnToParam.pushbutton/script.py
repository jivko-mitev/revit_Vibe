# -*- coding: utf-8 -*-
from pyrevit import revit, DB

doc = revit.doc

# Име на параметъра в колоните
PARAM_NAME = "bimU_Column_Reinforcement"

# Вземаме всички колони
columns = DB.FilteredElementCollector(doc) \
    .OfCategory(DB.BuiltInCategory.OST_StructuralColumns) \
    .WhereElementIsNotElementType() \
    .ToElements()

t = DB.Transaction(doc, "Write Column Reinforcement")
t.Start()

for col in columns:

    # Всички армировки в документа
    rebars = DB.FilteredElementCollector(doc) \
        .OfClass(DB.Structure.Rebar) \
        .WhereElementIsNotElementType() \
        .ToElements()

    rebar_data = {}

    for rebar in rebars:
        # Проверка дали армировката принадлежи към колоната
        host = rebar.GetHostId()
        if host != col.Id:
            continue

        # --- ЧЕТЕНЕ НА ПАРАМЕТРИ ---

        # Rebar Number
        p_number = rebar.LookupParameter("Rebar Number")
        if not p_number:
            continue
        rebar_number = p_number.AsString()

        # Quantity
        p_qty = rebar.LookupParameter("Quantity")
        qty = p_qty.AsInteger() if p_qty else 0

        # Bar Diameter (в mm)
        p_diam = rebar.LookupParameter("Bar Diameter")
        if p_diam:
            diam_internal = p_diam.AsDouble()
            diam_mm = int(DB.UnitUtils.ConvertFromInternalUnits(
                diam_internal,
                DB.UnitTypeId.Millimeters
            ))
        else:
            diam_mm = 0

        # Rounded_Length (в cm)
        p_len = rebar.LookupParameter("Rounded_Length")
        if p_len:
            len_internal = p_len.AsDouble()
            len_cm = int(DB.UnitUtils.ConvertFromInternalUnits(
                len_internal,
                DB.UnitTypeId.Centimeters
            ))
        else:
            len_cm = 0

        # --- ГРУПИРАНЕ ---
        if rebar_number not in rebar_data:
            rebar_data[rebar_number] = {
                "qty": 0,
                "diam": diam_mm,
                "len": len_cm
            }

        rebar_data[rebar_number]["qty"] += qty

    # --- СОРТИРАНЕ ПО Rebar Number ---
    sorted_keys = sorted(rebar_data.keys(), key=lambda x: int(x) if x.isdigit() else x)

    lines = []

    for key in sorted_keys:
        data = rebar_data[key]

        line = u"поз.{0} {1}N{2}x{3}".format(
            key,
            data["qty"],
            data["diam"],
            data["len"]
        )

        lines.append(line)

    result_text = "\r\n".join(lines)

    # --- ЗАПИС В ПАРАМЕТЪРА ---
    param = col.LookupParameter(PARAM_NAME)
    if param and not param.IsReadOnly:
        param.Set(result_text)

t.Commit()

print("Готово ✔")