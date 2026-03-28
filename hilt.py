"""Sibling to blade.py, handle creation of crossguard and hilts."""

import bpy
import bmesh
from mathutils import Vector
from math import sin, cos, pi 
from functools import partial

from blade import create_blade 
from utils import create_surface, create_d_peg, create_cylinder
from utils import SEGMENTS, BAR_DIAMETER, BAR_RADIUS, HILT_LENGTH_ONE_HAND, CROSSGUARD_NORMAL, CROSSGUARD_THICKNESS, CROSSGUARD_DEPTH, DEFAULT_PEG_RADIUS, DEFAULT_SLOT_RADIUS

from typing import Dict, List, Tuple, Optional, Union, Any

# Parameters. See utils for the one imported.


def offset_point(point, offset_value: float, offset_index: int):
    point = list(point)
    point[offset_index] += offset_value
    return point

def create_diamond_shape(bm, offset=(0, 0, 0), direction_index=1, radius=0.03, length=0.1, tip_radius=0.01):
    """Crude version. Sprouting a cube-esque shape from offset toward direction_index axis. Each tip is a tip_radius square to prevent edges.
    TODO allow an arbitrary direction vector that will generate matching """
    sx, sy, sz = offset 
    center = offset_point(offset, length / 2, direction_index) # the center of the shape
    end_offset = offset_point(offset, length, direction_index) # the tip of the shape 
    # construct points
    points = []
    for di in range(3):
        if di == direction_index:
            continue 
        for r in [-1, 1]:
            # start and end point of tipmost faces
            start_point = bm.verts.new(offset_point(offset, r*tip_radius, di))
            end_point = bm.verts.new(offset_point(end_offset, r*tip_radius, di))
            # center of the vertex-like near the diamond
            tip_center = offset_point(center, r*radius, di)
            # matchin start and end point 
            tip_start_point = bm.verts.new(offset_point(tip_center, (radius/abs(radius))*tip_radius, direction_index))
            tip_end_point = bm.verts.new(offset_point(tip_center, -(radius/abs(radius))*tip_radius, direction_index))
            # the other side points needed
            other_index = next((i for i in range(3) if i != direction_index and i != di))
            tip_side_points = [bm.verts.new(offset_point(tip_center, -tip_radius, other_index)), bm.verts.new(offset_point(tip_center, tip_radius, other_index))]
            points.append([start_point, tip_start_point, tip_end_point, end_point, tip_side_points])
    bm.verts.ensure_lookup_table()
    # 2nd - iterate throught points and connect into faces. 
    # need to reorder to form relevant section
    ordered_points = [points[i] for i in [0, 2, 1, 3]]
    for i, (sp, tsp, tep, ep, sps) in enumerate(ordered_points): # start_point, tip_start_point etc.
        nsp, ntsp, ntep, nep, nsps = ordered_points[(i+1)%len(ordered_points)] # next_ whatever 
        # print(sps, nsps)
        # connect. First find closest side pairs to use 
        bs, nbs = min( ((p, np) for p in sps for np in nsps), key=lambda args: (args[0].co-args[1].co).length) # best_side, next_best_side etc 
        # create faces 
        bm.faces.new([sp, nsp, ntsp, tsp])
        bm.faces.new([tsp, ntsp, nbs, bs])
        bm.faces.new([bs, nbs, ntep, tep])
        bm.faces.new([tep, ntep, nep, ep])
        # also construct the half faces that match bs/nbs 
        bm.faces.new([bs, tsp, tep])
        bm.faces.new([nbs, ntsp, ntep])
    # after done, also form the end faces 
    bm.faces.new([ps[-2] for ps in ordered_points])
    # return the faces that formed at the start point
    return bm, [ps[0] for ps in ordered_points]

def create_basic_hilt(bm, offset=(0, 0, 0), crossguard_dim=(1.0, 0.2, 0.08), hilt_dim=(0.08, 0.75), slot_radius: float=DEFAULT_SLOT_RADIUS):
    """Version 1: very basic crucifix hilt with diamond-shaped tips and pommels."""
    clength, cwidth, cdepth = crossguard_dim 
    hradius, hlength = hilt_dim 
    # create the two opposite diamond at end of crossguard 
    tip_radius = cdepth / 4
    ox, oy, oz = offset
    bm, diamond_left  = create_diamond_shape(bm, (ox-clength/2+tip_radius*3, oy, oz), direction_index=0, radius=tip_radius*1.5, length=-tip_radius*3, tip_radius=tip_radius)
    bm, diamond_right = create_diamond_shape(bm, (ox+clength/2-tip_radius*3, oy, oz), direction_index=0, radius=tip_radius*1.5, length=tip_radius*3, tip_radius=tip_radius)
    # should have matching sections; since we are generating x axis, the diamond vertices should be both -y -> -z -> y -> z; generate appropriate points for the crossguard 
    # print([d.co for d in diamond_left], [d.co for d in diamond_right])
    top_points, bottom_points = list(), list()
    for ydir in [-1, 1]:
        # face_indexes are always -z - (+-x) + z)
        if ydir == -1:
            face_indexes = [1, 0, -1]
        else:
            face_indexes = [1, 2, 3]
        new_verts = [bm.verts.new([ox, oy+ydir*cwidth/2, oz-tip_radius]), bm.verts.new([ox, oy+ydir*cwidth/2+tip_radius, oz]), bm.verts.new([ox, oy+ydir*cwidth/2, oz+tip_radius])]
        for i in range(2):
            # construct faces for each version 
            bm.faces.new([new_verts[i], new_verts[i+1], diamond_left[face_indexes[i+1]], diamond_left[face_indexes[i]]])
            bm.faces.new([new_verts[i], new_verts[i+1], diamond_right[face_indexes[i+1]], diamond_right[face_indexes[i]]])
        top_points.append(new_verts[-1])
        bottom_points.append(new_verts[0])
    
    # create the hilt
    bm, hilt_bottom = create_cylinder(bm, center=(ox, oy, oz-(cdepth-tip_radius)), radius=hradius, height=-hlength)
    # restructure and join the bottom together.
    bottom = [bottom_points[0], diamond_right[1], bottom_points[1], diamond_left[1]]
    create_surface(bm, bottom, hilt_bottom)
    # create the slot for inserting blade peg
    bm, slot_base = create_d_peg(bm, center=(ox, oy, oz+tip_radius), radius=slot_radius)
    top = [diamond_left[-1], top_points[1], diamond_right[-1], top_points[0]]
    create_surface(bm, slot_base, top)


# this should return the `bottom` verts; which in inverted height actually mean the top ones
create_generic_hilt = partial(create_cylinder, height=-HILT_LENGTH_ONE_HAND, closed_bottom=False, closed_top=True) 

def create_generic_crossguard(bm, offset=(0, 0, 0), length: float=CROSSGUARD_NORMAL*2, width: float=CROSSGUARD_THICKNESS*2, depth: float=CROSSGUARD_DEPTH, tip_width: float=None):
    """Simple straight crossguard, only taper from width to tip_width.
    `length`/`width` are the ENTIRE length/width of the crossguard; so need to x2 on values (which mostly function like radius)
    """
    ox, oy, oz = offset  
    tip_width = tip_width or depth # if not supply tip_width, use no taper 
    tip_radius, center_radius, depth_radius = tip_width / 2, width / 2, depth / 2
    # fixed creation dimension to y 
    direction_index = 0
    # generate 4 corner points along this dimension index
    corners = [(0, 1, 1), (0, 1, -1), (0, -1, -1), (0, -1, 1)]
    points = [list() for _ in range(3)] # this contain left-tip, center, right tip points
    for rx, ry, rz in corners:
        left_tip    = bm.verts.new([ox - length / 2, oy + ry*tip_radius, oz + rz*depth_radius])
        center      = bm.verts.new([ox, oy + ry*center_radius, oz + rz*depth_radius])
        right_tip   = bm.verts.new([ox + length / 2, oy + ry*tip_radius, oz + rz*depth_radius])
        points[0].append(left_tip); points[1].append(center); points[2].append(right_tip)
    bm.verts.ensure_lookup_table()
    # construct faces surround the blade, identifying top & bottom surfaces.
    bm.faces.new(points[0]); bm.faces.new(points[-1]) # left/right tip surface 
    # side surfaces
    bm.faces.new(points[0][:2] + points[1][:2][::-1])
    bm.faces.new(points[-1][:2] + points[1][:2][::-1])
    bm.faces.new(points[0][-2:] + points[1][-2:][::-1])
    bm.faces.new(points[-1][-2:] + points[1][-2:][::-1])
    top_verts = [points[i][0] for i in range(3)] + [points[i][3] for i in range(3)][::-1]
    bottom_verts = [points[i][1] for i in range(3)] + [points[i][2] for i in range(3)][::-1]
    return bm, top_verts, bottom_verts

def create_profiled_crossguard(bm, profile_fn: callable, offset=(0, 0, 0), length: float=CROSSGUARD_NORMAL*2, width: float=CROSSGUARD_THICKNESS*2, depth: float=CROSSGUARD_DEPTH, tip_width: float=None, **kwargs):
    """Slightly enhanced - a function profile_fn is used to generate a profile of the tip at opposite ends, which will then be linked together in a similar "profile" to the above tapering.
    """
    tip_width = tip_width or depth # if not supply tip_width, use no taper 
    ox, oy, oz = offset 
#    print(kwargs)
    bm, left_profile = profile_fn(bm, offset=(ox - length/2, oy, oz), original_point=offset, radius=tip_width/2, **kwargs)
    bm, right_profile = profile_fn(bm, offset=(ox + length/2, oy, oz), original_point=offset, radius=tip_width/2, **kwargs)
    # for each of these profile, the 1st and middle point will be top and bottom respectively and will have specialized keep mechanism  
    assert len(left_profile) == len(right_profile)
    bottom_index = len(left_profile) // 2
    # trigger for front variant 
    front_offset = Vector((0, width / 2, 0))
    front_profiles = left_profile[:bottom_index+1], right_profile[:bottom_index+1]
    front_vertices = [bm.verts.new( ( vl.co + vr.co ) / 2 + front_offset) for vl, vr in zip(*front_profiles)]
    # create new faces on the front
    for i in range(len(front_vertices)-1):
        center_current, center_next = front_vertices[i], front_vertices[i+1]
        left_current, left_next = front_profiles[0][i], front_profiles[0][i+1]
        right_current, right_next = front_profiles[1][i], front_profiles[1][i+1]
        bm.faces.new([center_current, center_next, left_next, left_current])
        bm.faces.new([center_current, center_next, right_next, right_current]) 
    # trigger for back variant
    back_offset = Vector((0, -width / 2, 0))
    back_profiles = left_profile[bottom_index:] + left_profile[:1], right_profile[bottom_index:] + right_profile[:1]
    back_vertices = [bm.verts.new( ( vl.co + vr.co ) / 2 + back_offset) for vl, vr in zip(*back_profiles)]
    # create new faces on the back
    for i in range(len(back_vertices)-1):
        center_current, center_next = back_vertices[i], back_vertices[i+1]
        left_current, left_next = back_profiles[0][i], back_profiles[0][i+1]
        right_current, right_next = back_profiles[1][i], back_profiles[1][i+1]
        bm.faces.new([center_current, center_next, left_next, left_current])
        bm.faces.new([center_current, center_next, right_next, right_current])
    
    # retrieve faces for top/bottom surface to allow binding
    top = [left_profile[0], front_vertices[0], right_profile[0], back_vertices[-1]]
    bottom = [left_profile[bottom_index], front_vertices[-1], right_profile[bottom_index], back_vertices[0]]

    return bm, top, bottom


def create_profiled_hilt(bm, profile_fn: callable, offset=(0, 0, 0), radius=BAR_RADIUS, height=-HILT_LENGTH_ONE_HAND, segments=SEGMENTS, use_profile_as_base: bool=True, **kwargs):
    """Similar to create_profiled_crossguard; this allow a profiled function to form the pommel of the hilt and construct the hilt based on this."""
    ox, oy, oz = offset 
    profile_offset = (ox, oy, oz+height)
    bm, profile_surface = profile_fn(bm, offset=profile_offset, original_point=offset, radius=radius, **kwargs)
    # simply clone the profile into a cylinder around the original offset 
    if not use_profile_as_base:
        # explicitly set and use this when profile is of uncertain shape; create a slight offset bottom profile and link them up via create_surface; then replace profile_surface with the new bottom_profile
        angle_perc = pi * 2 / segments 
        spaced_height = height * (abs(height) - abs(radius/4)) / abs(height)
        bottom_profile = [bm.verts.new([ox + sin(angle_perc*i)*radius, oy + cos(angle_perc*i)*radius, oz+spaced_height]) for i in range(segments)]
        create_surface(bm, bottom_profile, profile_surface)
        profile_surface = bottom_profile 
    top_profile = [bm.verts.new([p.co.x, p.co.y, oz]) for p in profile_surface]
    # regardless of mode; upon reaching here the top_profile and bottom_profile should match completely.
    for i in range(len(top_profile)):
        v1 = top_profile[i]
        v2 = top_profile[(i+1) % len(top_profile)]
        v3 = profile_surface[(i+1) % len(top_profile)]
        v4 = profile_surface[i]
        bm.faces.new([v1, v2, v3, v4])
    # return the top_profile as is 
    return bm, top_profile



def profile_flat_circle(bm, offset=(0, 0, 0), original_point=(-1, 0, 0), radius=0.05, segments=SEGMENTS):
    """Simply create a flat circle on offset on Oyz plane."""
    ox, oy, oz = offset
    angle_perc = pi * 2 / segments
    points = [bm.verts.new([ox, oy + radius*sin(angle_perc*i), oz + radius * cos(angle_perc*i)]) for i in range(segments)]
    bm.faces.new(points)
    return bm, points

create_rounded_crossguard = lambda bm, **kwargs: create_profiled_crossguard(bm, profile_flat_circle, **kwargs)

def profile_ball(bm, offset=(0, 0, 0), original_point=(-1, 0, 0), radius=0.05, segments=SEGMENTS):
    """Similar to profile_flat_circle, this return a flat circle as the profile; but it also spawn a ball sqrt2 from the offset. Make this generalized so that it can also be used as part of the hilt mechanism."""
    direction_index = max(range(3), key=lambda i: abs(offset[i]-original_point[i]))
    offset_raw = offset[direction_index] - original_point[direction_index]
    offset_sign = offset_raw / abs(offset_raw)
    # calculate true radius and true ball center 
    true_radius = radius * 1.41
    center = list(offset)
    center[direction_index] += offset_sign * radius # center is `radius` away; being 45 deg from original 
    center_vector = Vector(center)
    all_points = []
    angle_perc = pi * 2 / segments
#    print("@profile_ball: received radius", radius, "surface_radius: ", sin(angle_perc * (segments / 8)))
    aux1_index, aux2_index = [d for d in range(3) if d != direction_index] # prioritize x->y->z
    for i in range(segments // 4,  segments): # skip the segments before the 45 deg mark, iterate along the original direction
        new_points = list()
        vector = list(center)
        vector[direction_index] += offset_sign * -cos(angle_perc * i / 2) * true_radius 
        # print("R", i, "zoff", -cos(angle_perc * i / 2))
        for j in range(segments):
            # form the circle around each iteration location
            vector[aux1_index] = center[aux1_index] + sin(angle_perc * i / 2) * sin(angle_perc * j) * true_radius 
            vector[aux2_index] = center[aux2_index] + sin(angle_perc * i / 2) * cos(angle_perc * j) * true_radius 
            new_points.append(bm.verts.new(vector))
        # append into the total point list 
        all_points.append(new_points)
    # construct faces 
    bm.verts.ensure_lookup_table()
    for i in range(segments):
        for j in range(len(all_points)-1):
            v1 = all_points[j][i]
            v2 = all_points[j+1][i]
            v3 = all_points[j+1][(i+1)%segments]
            v4 = all_points[j][(i+1)%segments]
            bm.faces.new([v1, v2, v3, v4])
    # also seal the last iteration together. TODO allow an additional protrusion
    bm.faces.new(all_points[-1])
    # first iteration recorded will be the profile given for construction
    return bm, all_points[0]


create_ball_ended_crossguard = lambda bm, **kwargs: create_profiled_crossguard(bm, profile_ball, **kwargs)
create_ball_pommel_hilt = lambda bm, **kwargs: create_profiled_hilt(bm, profile_ball, **kwargs)

def profile_dish(bm, offset=(0, 0, 0), original_point=(-1, 0, 0), radius=0.05, dish_thickness=None, segments=SEGMENTS):
    """One of the most common pommel, this is a sideway dish that is aligned with the blade direction. For now this is hardcoded to priortize and follow x axis. Created profile will remain a circle centering on offset.
    Will still use sqrt2 as it's the cheapest compatible deg for 16 segment models
    
    dish_thickness is 2/3 of the radius (thus, 1/3 of diameter) unless explicitly set.
    """
    ox, oy, oz = offset 
    direction_index = max(range(3), key=lambda i: abs(offset[i]-original_point[i]))
    assert direction_index != 1, "@profile_dish: cannot accept y direction atm"
    other_index = 2 if direction_index == 0 else 0 # must be 0-2 pair
    offset_raw = offset[direction_index] - original_point[direction_index]
    offset_sign = offset_raw / abs(offset_raw)
    true_radius = radius * 1.41 
    center = list(offset)
    center[direction_index] += offset_sign * true_radius 
    cx, cy, cz = center
    front, back = list(), list()
    angle_perc = pi * 2 / segments 
    thickness = dish_thickness or (radius * 0.66)
    for i in range(segments // 8, segments - segments // 8 + 1):
        point = list(center)
        point[direction_index] += -offset_sign*cos(angle_perc*i)*true_radius 
        point[other_index] += sin(angle_perc*i)*true_radius
        # create the relevant disk with appropriate thickness. thickness direction will be on y axis
        point[1] = cy + thickness / 2
        front.append(bm.verts.new(point))
        point[1] = cy - thickness / 2
        back.append(bm.verts.new(point))
    # form up the faces 
    bm.verts.ensure_lookup_table()
    for i in range(len(front) - 1):
        bm.faces.new([front[i], front[i+1], back[i+1], back[i]])
    bm.faces.new(front)
    bm.faces.new(back)
    # create additional top/bottom nodes to ensure crossguard can create appropriate top/bottom faces  
    point = list(offset)
    point[other_index] += radius
    top_vert = bm.verts.new(point)
    point[other_index] -= 2*radius #(=-radius)
    bottom_vert = bm.verts.new(point)
    profile_surface = [top_vert, front[0], front[-1], bottom_vert, back[-1], back[0]]
    # print(profile_surface)
    return bm, profile_surface
    
# this should have specified thickness 
create_dish_ended_crossguard = lambda bm, **kwargs: create_profiled_crossguard(bm, profile_dish, **kwargs)
create_dish_hilt = lambda bm, **kwargs: create_profiled_hilt(bm, profile_dish, use_profile_as_base=False, **kwargs)

def profile_nub(bm, offset=(0, 0, 0), original_point=(-1, 0, 0), radius=0.05, segments=SEGMENTS):
    """Stylized round nub; pretty much a ball but with the point cos-diff during the first contacting half"""
    direction_index = max(range(3), key=lambda i: abs(offset[i]-original_point[i]))
    offset_raw = offset[direction_index] - original_point[direction_index]
    offset_sign = offset_raw / abs(offset_raw)
    # calculate true radius and true ball center 
    true_radius = radius * 1.41
    center = list(offset)
    center[direction_index] += offset_sign * radius # center is `radius` away; being 45 deg from original 
    center_vector = Vector(center)
    all_points = []
    angle_perc = pi * 2 / segments
#    print("@profile_ball: received radius", radius, "surface_radius: ", sin(angle_perc * (segments / 8)))
    aux1_index, aux2_index = [d for d in range(3) if d != direction_index] # prioritize x->y->z
    for i in range(segments): # no longer skip the segments before the 45 deg mark since the front half are forming the inverted nub now
        new_points = list()
        vector = list(center)
        vector[direction_index] += offset_sign * -cos(angle_perc * i / 2) * true_radius  
        if i < segments // 2:
            if i % 2 != 0:
                continue # slash half of the faces to prevent pointless 
            # this is first half, the ratio will be swapped from sin -> (1-cos);
            xy_radius = radius + (1 - cos(angle_perc * i / 2)) * (true_radius - radius)
        else:
            # default, will have radius compensating for cos like a normal ball
            xy_radius = sin(angle_perc * i / 2) * true_radius
        # print("R", i, "zoff", -cos(angle_perc * i / 2))
        for j in range(segments):
            # form the circle around each iteration location
            vector[aux1_index] = center[aux1_index] + xy_radius * sin(angle_perc * j) 
            vector[aux2_index] = center[aux2_index] + xy_radius * cos(angle_perc * j) 
            new_points.append(bm.verts.new(vector))
        # append into the total point list 
        all_points.append(new_points)
    # construct faces 
    bm.verts.ensure_lookup_table()
    for i in range(segments):
        for j in range(len(all_points)-1):
            v1 = all_points[j][i]
            v2 = all_points[j+1][i]
            v3 = all_points[j+1][(i+1)%segments]
            v4 = all_points[j][(i+1)%segments]
            bm.faces.new([v1, v2, v3, v4])
    # also seal the last iteration together. TODO allow an additional protrusion
    bm.faces.new(all_points[-1])
    # first iteration recorded will be the profile given for construction
    return bm, all_points[0]

# this should have specified thickness 
create_nub_ended_crossguard = lambda bm, **kwargs: create_profiled_crossguard(bm, profile_nub, **kwargs)
create_nub_pommel_hilt = lambda bm, **kwargs: create_profiled_hilt(bm, profile_nub, **kwargs)


def create_expanded_d_peg(bm, center=(0, 0, 0), radius=-0.1, height=-0.04, segments=SEGMENTS, expand_ratio=(1.1, 1.5, 1.0), lug_size:float=0.005, lug_position: float=None):
    """Same d peg but (1) expanded base for firmer peg and (2) with additional lugs to make tighter attach. Since models might not """
    raise NotImplementedError
    verts_top = []
    verts_bottom = []

    cx, cy, cz = center
    for i in range(segments):
        angle = 2 * pi * i / segments
        # Only keep right half (X ≥ 0)
        if sin(angle) >= -0.001:
            x = radius * sin(angle)
            y = radius * cos(angle)
            v_bot = bm.verts.new((x + cx, y + cy, cz))
            v_top = bm.verts.new((x + cx, y + cy, cz + height))
            verts_bottom.append(v_bot)
            verts_top.append(v_top)
            # print("added ", cos(angle), sin(angle))

    # Add flat back face on X = -radius
    v1_bottoms = [bm.verts.new((cx - radius, cy + y, cz)) for y in [-radius, 0, radius]]
    v1_tops = [bm.verts.new((cx - radius, cy + y, cz + height)) for y in [-radius, 0, radius]]
    verts_bottom.extend(v1_bottoms)
    verts_top.extend(v1_tops)

    # Side walls
    size = len(verts_bottom)
    for i in range(size):
        v1 = verts_bottom[i]
        v2 = verts_bottom[(i + 1) % size]
        v3 = verts_top[(i + 1) % size]
        v4 = verts_top[i]
        bm.faces.new([v1, v2, v3, v4])

    # Cap top
    bm.faces.new(verts_top) 
    # try to give correctly oriented nodes 
    # peg_bottom = verts_bottom[-3:] + verts_bottom[:-3]
    # peg_bottom = verts_bottom[-1:] + verts_bottom[:-1]
    peg_bottom = verts_bottom
    return bm, peg_bottom


"""Generic creation function."""

def create_hilt_format(**kwargs):
    return partial(create_hilt, **kwargs)

def create_hilt(bm, crossguard_generator: callable, hilt_generator: callable, slot_generator: callable=None, crossguard_kwargs: Optional[dict]=dict(), hilt_kwargs: Optional[dict]=dict(), slot_kwargs: Optional[dict]=dict(), no_slot: bool=False):
    """Generalized version in the same vein as create_blade.
    crossguard_generator should generate the crossguard and return the top and bottom surface suitable for attaching; slot_generator will generate a slotted indent on the top section, hilt_generator will generate the hilt attaching to the bottom section.
    hilt_generator generate a minifig-compatible hilt that can be held by the minifig neatly.
    slot_generator is just peg_generator but inverted.
    """
    bm, top, bottom = crossguard_generator(bm, **crossguard_kwargs)
    # create the hilt
    bm, hilt_bottom = hilt_generator(bm, **hilt_kwargs)
    # restructure and join the bottom together.
    create_surface(bm, hilt_bottom, bottom)
    if no_slot:
        # if engaging no_peg, return the surface to connect
        return bm, top
    # create the slot for inserting blade peg
    bm, slot_base = slot_generator(bm, **slot_kwargs)
    create_surface(bm, slot_base, top)
    return bm  

def create_full_blade_format(**kwargs):
    return partial(create_full_blade, **kwargs)

def create_full_blade(bm, 
                      blade_generator: callable=None, surface_generator: callable=None, blade_kwargs: Optional[dict]=dict(), surface_kwargs: Optional[dict]=dict(), # these are blade args.
                      crossguard_generator: callable=None, hilt_generator: callable=None, crossguard_kwargs: Optional[dict]=dict(), hilt_kwargs: Optional[dict]=dict()):
    # simply create the blade and hilt with no_peg and no_slot respectively and join them together 
    bm, blade_surface = create_blade(bm, blade_generator=blade_generator, surface_generator=surface_generator, blade_kwargs=blade_kwargs, surface_kwargs=surface_kwargs, no_peg=True)
    # Since crossguard generated at its center; the crossguard need to be generated at -depth/2 and the hilt at -depth
    crossguard_depth = crossguard_kwargs.get("depth", CROSSGUARD_DEPTH)
    crossguard_kwargs["offset"] = crossguard_kwargs.get("offset", (0, 0, -crossguard_depth/2))
    hilt_kwargs["offset"] = hilt_kwargs.get("offset", (0, 0, -crossguard_depth))
    bm, hilt_surface = create_hilt(bm, crossguard_generator=crossguard_generator, hilt_generator=hilt_generator, crossguard_kwargs=crossguard_kwargs, hilt_kwargs=hilt_kwargs, no_slot=True)
    create_surface(bm, blade_surface, hilt_surface)
    return bm 

# all combination that is working relatively OK. Organized as pair of crossguard_generator/hilt_generator
HILT_VARIATIONS = {
        "plain": (create_generic_crossguard, create_generic_hilt), 
        "ball": (create_ball_ended_crossguard, create_ball_pommel_hilt),
        "dish": (create_dish_ended_crossguard, create_dish_hilt),
        "nub": (create_nub_ended_crossguard, create_nub_pommel_hilt)
}
