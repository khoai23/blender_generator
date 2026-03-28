"""Handle generating cool straight blades for longswords. Warden inspired."""

import bpy
import bmesh
from mathutils import Vector
from math import sin, cos, pi, atan2 
from functools import partial

from utils import create_surface, create_meshes, form_side_surfaces, create_d_peg
from utils import SEGMENTS, BLADE_THICKNESS, BLADE_WIDTH, BLADE_LENGTH_DEFAULT, BLADE_LENGTH_LONG, BLADE_LENGTH_MASSIVE

from typing import Dict, List, Tuple, Optional, Union, Any

# Parameters. See utils for the orignal composition 
# these defaults are for scaling
DEFAULT_BLADE_RADII = base_radius, mid_radius, top_radius = 1.0, 0.75, 0.1
DEFAULT_BLADE_HEIGHTS = (BLADE_LENGTH_DEFAULT*3/4, BLADE_LENGTH_DEFAULT/4)
LONG_BLADE_HEIGHTS = (BLADE_LENGTH_LONG*7/8, BLADE_LENGTH_LONG/8)

RICASSO_BLADE_RADII = 1.0, 2.0, 0.75, 0.1
RICASSO_BLADE_HEIGHTS = (BLADE_LENGTH_MASSIVE/8, BLADE_LENGTH_MASSIVE/8, BLADE_LENGTH_MASSIVE/2, BLADE_LENGTH_MASSIVE/4)
# TODO need the ricasso variant too
BLADE_WIDTH_RADIUS = BLADE_WIDTH / 2
BLADE_THICKNESS_RADIUS = BLADE_THICKNESS / 2
SCALE = (BLADE_WIDTH_RADIUS, BLADE_THICKNESS_RADIUS)

def generate_oval_blade(bm, segments=SEGMENTS, radii=DEFAULT_BLADE_RADII, heights=DEFAULT_BLADE_HEIGHTS, scale=SCALE):
    """Type 1: oval, flattened from a circle, no flourish."""
    # unpack params
    base_radius, mid_radius, top_radius = radii
    height1, height2 = heights
    width, thickness = scale
    # Create base, mid and top ring
    base_verts = []
    mid_verts = []
    top_verts = []
    for i in range(segments):
        angle = (i / segments) * pi * 2
        x1 = base_radius * cos(angle) * width
        y1 = base_radius * sin(angle) * thickness
        x2 = mid_radius * cos(angle) * width
        y2 = mid_radius * sin(angle) * thickness
        x3 = top_radius * cos(angle) * width
        y3 = top_radius * sin(angle) * thickness
        
        v_base = bm.verts.new((x1, y1, 0))
        v_mid = bm.verts.new((x2, y2, height1))
        v_top = bm.verts.new((x3, y3, height1 + height2))
        base_verts.append(v_base)
        mid_verts.append(v_mid)
        top_verts.append(v_top)
        
    bm.verts.ensure_lookup_table()
    # Faces: base to mid, mid to top
    form_side_surfaces(bm, [base_verts, mid_verts, top_verts])
    # seal the top 
    bm.faces.new(top_verts)

    return bm, base_verts

def generate_surfaced_blade(bm, radii=DEFAULT_BLADE_RADII, heights=DEFAULT_BLADE_HEIGHTS, scale=SCALE, segments=SEGMENTS):
    """Type 2: oval, flattened from a circle with a prepared surface for the fuller. Should be compatible with create_blade."""
    # unpack params
    base_radius, mid_radius, top_radius = radii
    height1, height2 = heights
    width, thickness = scale
    # Create base, mid and top ring
    base_verts = []
    mid_verts = []
    top_verts = []
 
    max_thickness = base_radius * thickness / 1.71
    section_size = segments // 8 
    for i in range(segments):
        angle = (i / segments) * pi * 2
        x1 = base_radius * cos(angle) * width
        y1 = base_radius * sin(angle) * thickness 
        if all((abs(i-cp) > section_size for cp in [0, segments // 2, segments])):
            # this avoid the center region and form a flat surface
            continue
        x2 = mid_radius * cos(angle) * width
        y2 = mid_radius * sin(angle) * thickness
        x3 = top_radius * cos(angle) * width
        y3 = top_radius * sin(angle) * thickness
        
        v_base = bm.verts.new((x1, y1, 0))
        v_mid = bm.verts.new((x2, y2, height1))
        v_top = bm.verts.new((x3, y3, height1 + height2))
        base_verts.append(v_base)
        mid_verts.append(v_mid)
        top_verts.append(v_top)
        
    bm.verts.ensure_lookup_table()
    # Faces: top cap, base to mid, mid to top 
    # skip the faces for half the segment nodes; hence this should target +section_size and -section_size(-1) to ignore those faces.
    bm.faces.new(top_verts)
    vert_count = len(base_verts)
    front_face_index = (0, section_size)
    back_face_index = (0, vert_count - 1 - section_size)
    bm, excluded = form_side_surfaces(bm, [base_verts, mid_verts, top_verts], exclude_faces=[front_face_index, back_face_index])
    flats = [excluded[front_face_index], excluded[back_face_index]]
    return bm, base_verts, flats



def create_generic_fuller(bm, offset=(0, 0, 0), width: float=BLADE_WIDTH*0.8, length: float=BLADE_LENGTH_DEFAULT*0.75, depth: float=BLADE_THICKNESS/8, segment=SEGMENTS):
    """No more trickery. Create a surface representing the fuller that can be appended to a flat-sided blade surface. Biding the outer surface to the blade can be done later as a companion function.
    Return the outer surface later."""
    ox, oy, oz = offset
    # form the dome-surface of the fuller. This one's radius should be half width; so center should be length-radius 
    radius = width / 2
    segment_angle = pi / segment # segments are counted along the 180 deg
    dome_center_x, dome_center_y, dome_center_z = ox, oy, oz + length - radius  
    # topmost point will be the end of length
    top_point = bm.verts.new([ox, oy, oz + length])
    points_array = [[(top_point)]]
    for iy in range(segment // 2 - 1):
        # iterate downward from the top along z axis, only 90 deg so iteration is half
        slice_ratio = sin((iy+1) * segment_angle)
        vz = dome_center_z + cos((iy+1) * segment_angle) * radius
        # building vertices and then connect faces
        prev_point_array = points_array[iy]
        # form vertices
        next_point_array = [] 
        for ix in range(segment):
            # create points; all 180 deg starting from -90 to + 90 
            # X need to go -1 to 1 in 180
            vx = dome_center_x + sin(-pi / 2 + ix * segment_angle) * slice_ratio * radius 
            # Y need to go 0 -> 1 -> 0 in 180 too; but this also need to be distorted with tapering
            vy = dome_center_y + sin(ix * segment_angle) * slice_ratio * depth 
            #print("ADD: ", iy, ix, "->", cos((iy+1) * segment_angle), sin(-pi / 2 + ix * segment_angle), sin(ix * segment_angle))
            next_point_array.append(bm.verts.new([vx, vy, vz]))
        # form faces 
        for i in range(segment-1):
            if len(prev_point_array) == 1:
                # create triangle faces when there is only 1 point to connect to
                bm.faces.new([prev_point_array[0], next_point_array[i], next_point_array[i+1]])
            else:
                # create quadilateral faces if previous point array is NOT 1 point 
                bm.faces.new([prev_point_array[i+1], prev_point_array[i], next_point_array[i], next_point_array[i+1]])
        # after done, append points to section
        points_array.append(next_point_array)
    # forming the 2nd face flattening back into original blade surface 
    existing_points = points_array[-1]
    # forming vertices and faces down in the bottom
    def downpoint(point, bm=bm):
        x, y, z = point.co 
        return bm.verts.new([x, y, oz + abs(y - oy)])
    new_points = [downpoint(e) for e in existing_points]
    for face_point in zip(existing_points[:-1], existing_points[1:], new_points[1:], new_points[:-1]):
        bm.faces.new(face_point)
    bm.faces.new(new_points)
    # TODO return the appropriate surface points to allow integration with the rest of the sword
    surface_points = [new_points[0]] + [pa[0] for pa in points_array[1:]][::-1] + points_array[0] + [pa[-1] for pa in points_array[1:]] + [new_points[-1]]
    return bm, surface_points

def create_double_fuller(bm, offset=(0, 0, 0), width: float=BLADE_WIDTH*0.8, distance: float=None, **kwargs):
    """Reuse the above single fuller; plus adding the flat surface between them.
    width is the total width occupied by the fuller. This should make this consistent with the 1-fuller version too.
    """
    # create the 1st part with different offset 
    ox, oy, oz = offset 
    if distance is None:
        distance = width / 5
    fuller_width = (width - distance) / 2
    fuller_offset = (fuller_width + distance) / 2 # radius + half distance
    _, fs1 = create_generic_fuller(bm, offset=(ox - fuller_offset, oy, oz), width=fuller_width, **kwargs) # fuller_surface_1 etc
    _, fs2 = create_generic_fuller(bm, offset=(ox + fuller_offset, oy, oz), width=fuller_width, **kwargs)
    # add surface between the end half of 1 and the front half of 2. Actually doesn't need any inversion
    count = (len(fs1)+1) // 2
    bm.faces.new(fs1[-count:] + fs2[:count])
    # return the other points as the new surfaces, keeping the external 4 points of the new surface (fs1[count], fs2[coutnt] in the slice; fs1[-1] and fs2[0] manually in the ending
    return bm, fs1[:count] + fs2[-count:] # + [fs2[0], fs1[-1]] 


def generate_ricasso_blade(bm, radii=RICASSO_BLADE_RADII, heights=RICASSO_BLADE_HEIGHTS, scale=SCALE, segments=SEGMENTS):
    """Create a blade with protrusion used for marking the sword ricasso. Radii/Height become 4/3 tuple respectively."""
    base_radius, protrude_radius, mid_radius, top_radius = radii
    hand_height, protrude_height, taper1_height, taper2_height = heights
    scale_width, scale_thickness = scale 
    all_points = [list() for _ in range(1+segments // 2 + 1 + 1)] # protrude section will take up segments /2 during iteration as it's half circle
    angle_perc = pi * 2 / segments
    protrusion_size = protrude_radius - base_radius
    for i in range(segments):
        angle = i * angle_perc 
        # add the base 
        v_base = bm.verts.new((mid_radius * cos(angle) * scale_width, mid_radius * sin(angle) *  scale_thickness, 0))
        all_points[0].append(v_base)
        # add the protrusion sections
        for j in range(segments // 2):
            x = (base_radius + protrusion_size * (1 - abs(cos(j * angle_perc)))) * cos(angle) * scale_width
            y = base_radius * sin(angle) * scale_thickness  
            z = hand_height + protrude_height / 2 * (j / (segments/2)) #* (1 + -cos(j*angle_perc) )
            all_points[j+1].append(bm.verts.new((x, y, z)))
        # add the mid/top point
        v_mid = bm.verts.new((mid_radius * cos(angle) * scale_width, mid_radius * sin(angle) *  scale_thickness, sum(heights[:-1])))
        v_top = bm.verts.new((top_radius * cos(angle) * scale_width, top_radius * sin(angle) *  scale_thickness, sum(heights)))
        all_points[-2].append(v_mid)
        all_points[-1].append(v_top)
        
    bm.verts.ensure_lookup_table()
    # Faces: base to mid, mid to top
    form_side_surfaces(bm, all_points)
    # seal the top 
    bm.faces.new(all_points[-1])

    return bm, all_points[0]


def create_blade_format(**kwargs):
    return partial(create_blade, **kwargs)

def create_blade(bm, blade_generator: callable, peg_generator: callable=None, surface_generator: callable=None, blade_kwargs: Optional[dict]=dict(), peg_kwargs: Optional[dict]=dict(), surface_kwargs: Optional[dict]=dict(), no_peg: bool=False):
    """Try to make a generic form. Allow superseeding all arguments during blade construction via {name}_kwargs"""
    bm, *additional = blade_generator(bm, **blade_kwargs)
    if len(additional) == 2:
        base, flats = additional 
        # for each of the flat side, generate the location and depth from the 
        for flat in flats:
            width = surface_kwargs.get("width", abs((flat[0].co - flat[-1].co)[0]) * 0.8) # width is proportional to flat total width, being x difference between 2 base line 
            offset_y = flat[0].co[1] # y of either base float will be the location
            depth = (-offset_y / abs(offset_y)) * surface_kwargs.get("depth", abs(offset_y) * 0.5)  # this is not only the actual depth of the fuller, but also decide the relevant direction
            length = surface_kwargs.get("length", flat[1].co[2] * 0.8) # length of fuller is proportional to base region length
            # create the flat surface 
            # print("Flat args: ", width, offset_y, depth, length)
            bm, flat_support = surface_generator(bm, offset=(0, offset_y, 0), width=width, depth=depth, length=length) 
            # join the surface together
            create_surface(bm, flat, flat_support, form_complete_surface=False)
    else:
        base = additional[0] 
    
    # if no_peg is set, return the base surface to join with other things elsewhere 
    if no_peg:
        return bm, base
    # else generate the peg to connect with other items
    bm, peg_base = peg_generator(bm, **peg_kwargs)
    create_surface(bm, base, peg_base)
    return bm

# all combination that is working relatively OK. Organized as pair of blade_generator/surface_generator
BLADE_VARIATIONS = {
        "plain": (generate_oval_blade, None), 
        "ricasso": (generate_ricasso_blade, None), 
        "1fuller": (generate_surfaced_blade, create_generic_fuller), 
        "2fuller": (generate_surfaced_blade, create_double_fuller)
}
