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
    return {
        "view_id": vp.ViewId,
        "center": vp.GetBoxCenter(),
        "type_id": vp.GetTypeId(),
        "rotation": vp.Rotation,
        "pinned": vp.Pinned,
        "label_offset": vp.LabelOffset if hasattr(vp, "LabelOffset") else None
    }


def restore_viewport(data, sheet_id):
    new_vp = Viewport.Create(doc, sheet_id, data["view_id"], data["center"])

    # тип
    if data["type_id"]:
        new_vp.ChangeTypeId(data["type_id"])

    # rotation
    try:
        new_vp.Rotation = data["rotation"]
    except:
        pass

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
    output.print_md("❌ Избери един Viewport.")
    script.exit()

selected = doc.GetElement(list(sel_ids)[0])

if not isinstance(selected, Viewport):
    output.print_md("❌ Това не е Viewport.")
    script.exit()

sheet_id = selected.SheetId

# всички viewport-и
viewports = get_viewports_on_sheet(sheet_id)

if len(viewports) <= 1:
    output.print_md("ℹ️ Само един Viewport в Sheet-а.")
    script.exit()

# кеш
vp_cache = []
selected_data = None

for vp in viewports:
    data = cache_viewport_data(vp)
    if vp.Id == selected.Id:
        selected_data = data
    else:
        vp_cache.append(data)

# нов ред → selected първи (най-отдолу)
ordered = [selected_data] + vp_cache

t = Transaction(doc, "Send Viewport To Back (Production)")
t.Start()

try:
    # unpin всички (ако има pinned)
    for vp in viewports:
        if vp.Pinned:
            vp.Pinned = False

    # delete
    for vp in viewports:
        doc.Delete(vp.Id)

    # recreate в ред
    for data in ordered:
        restore_viewport(data, sheet_id)

    t.Commit()
    output.print_md("✅ Viewport е преместен най-отдолу (production-ready).")

except Exception as e:
    t.RollBack()
    output.print_md("❌ Грешка: {}".format(str(e)))