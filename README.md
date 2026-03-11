# Blender Generator scripts

This is a repository for me to generate 3D objects, because I can't be arsed to properly learn Blender and make my life easier that way.

## How to use

Put this into the Blender's `Scripting` -> `Text Editor` to create a default plug-able sword parts or the complete sword. 

```
import sys
sys.path.append("D:/Project/blender_generator")

import blade
import utils

blade_mesh = utils.create_meshes(blade.create_blade, "Test_Blade_Part", blade_generator=blade.generate_oval_blade, peg_generator=blade.create_d_peg)

sword_mesh = utils.create_meshes(hilt.create_full_blade, "Test_Sword", blade_generator=blade.generate_surfaced_blade, surface_generator=blade.create_generic_fuller, crossguard_generator=hilt.create_ball_ended_crossguard, hilt_generator=hilt.create_ball_pommel_hilt)
sword_mesh.location = (20, 0, 0)

```

For now, the general idea is:
- Use `utils.create_meshes` whenever wanting to make a standard mesh, targeting the appropriate functions and argument.
- `blade.create_blade` are for plug-able blades (extruding peg). This accepts the following arguments:
  - `blade_generator`: Generating the main shape of the blade. This can accept standalone `generate_oval_blade`, `generate_ricasso_blade`; or `generate_surfaced_blade` which _requires_..
  - `surface_generator`: Only used along `generate_surfaced_blade`; this generate a surface on the blank slate of `generate_surfaced_blade`. Useful for fullers, and intend to upgrade to cooler surfaces later.
  - `peg_generator`: Generating the extruding peg. Only have D-shaped `create_d_peg` for now. If `no_peg=True`, this keep the underside open and can be joined with other parts. This becomes useful later with hilts.
- `hilt.create_hilt` are for plug-able hilts (intruding peg). This accept the following argument (already mostly detailed in the function):
  - `crossguard_generator`: Generating the crossguard object. This accepts `create_generic_crossguard` and `create_profiled_crossguard`variations. This is expected to leave two faces open, the upper one for the peg/blade connection and the upper one for the hilt connection
  - `hilt_generator`: Generating the hilt. This connect to the lower crossguard surface. Accepts `create_cylinder` for basic hilt, plus `create_profiled_hilt` variations.
  - `slot_generator`: Basically `peg_generator`; but since this is inside the upper crossguard surface, this will cause a slot instead.


## In Progress

The following are still not implemented, not yet workable or require further changes.
- `create_expanded_d_peg`: Need a better version of the peg mechanism. The current version is too easy to break off. Idea here is to create a reinforced version (flanged base) or maybe better to make it run blade's length instead. Additionally, can try to make a forked dual base which could maybe make it a lot easier to keep surface. Until then, full weapon creation is still priority.
- `shaft.py`: With `blade.py` already pretty decently, shaft making using the same nub mechanism can probably work to create generic polearms. This can be considered a radical case of `hilt.py`
- `axe.py`: Forming actual axehead, with the final goals of pollaxe/Ji/Glaive etc.
- `helmet.py`: Creating wearable helmet for Lego use.

