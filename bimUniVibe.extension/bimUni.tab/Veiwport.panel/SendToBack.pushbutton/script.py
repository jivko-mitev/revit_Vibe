# -*- coding: utf-8 -*-

from Autodesk.Revit.DB import *
from pyrevit import revit, script

doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()

# ----------------------------
# Helpers
# ----------------------------

def get_viewports_on_sheet(sheet_id):
    return [vp for vp in FilteredElementCollector(doc)
            .OfClass(Viewport)
            .ToElements()
            if vp.SheetId == sheet_id]


def cache_viewport_data(vp):
    outline = vp.GetBoxOutline()

    return {
        "view_id": vp.ViewId,
        "type_id": vp.GetTypeId(),
        "rotation": vp.Rotation,
        "pinned": vp.Pinned,
        "min_pt": outline.MinimumPoint,   # 🔥 ключово
        "max_pt": outline.MaximumPoint,
        "label_offset": vp.LabelOffset if hasattr(vp, "LabelOffset") else None
    }


def restore_viewport(data, sheet_id):
    # създаваме на произволна позиция
    new_vp = Viewport.Create(doc, sheet_id, data["view_id"], XYZ(0,0,0))

    # тип
    if data["type_id"]:
        new_vp.ChangeTypeId(data["type_id"])

    # rotation (преди move!)
    try:
        new_vp.Rotation = data["rotation"]
    except:
        pass

    # 🔥 ВЗИМАМЕ outline след rotation
    new_outline = new_vp.GetBoxOutline()

    new_min = new_outline.MinimumPoint
    target_min = data["min_pt"]

    # 🔥 ТОЧЕН ВЕКТОР (anchor към anchor)
    move_vector = target_min - new_min

    ElementTransformUtils.MoveElement(doc, new_vp.Id, move_vector)

    # label offset
    try:
        if data["label_offset"]:
            new_vp.LabelOffset = data["label_offset"]
    except:
        pass

    # pinned
    try:
        new_vp.Pinned = data["pinned"]
    except:
        pass

    return new_vp


# ----------------------------
# Main
# ----------------------------

sel_ids = uidoc.Selection.GetElementIds()

if not sel_ids:
    output.print_md("❌ Избери Viewport.")
    script.exit()

selected = doc.GetElement(list(sel_ids)[0])

if not isinstance(selected, Viewport):
    output.print_md("❌ Това не е Viewport.")
    script.exit()

sheet_id = selected.SheetId

viewports = get_viewports_on_sheet(sheet_id)

if len(viewports) <= 1:
    output.print_md("ℹ️ Само един Viewport.")
    script.exit()

# кеширане
vp_cache = []
selected_data = None

for vp in viewports:
    data = cache_viewport_data(vp)

    if vp.Id == selected.Id:
        selected_data = data
    else:
        vp_cache.append(data)

# ред: избраният първи (най-отдолу)
ordered = [selected_data] + vp_cache

t = Transaction(doc, "Ultimate Viewport Reorder (No Drift)")
t.Start()

try:
    # unpin
    for vp in viewports:
        if vp.Pinned:
            vp.Pinned = False

    # delete
    for vp in viewports:
        doc.Delete(vp.Id)

    # recreate
    for data in ordered:
        restore_viewport(data, sheet_id)

    t.Commit()
    output.print_md("🚀 Viewport е преместен най-отдолу.")

except Exception as e:
    t.RollBack()
    output.print_md("❌ Грешка: {}".format(str(e)))