import bpy
import bmesh
from mathutils import Vector
from math import pi, cos, sin, sqrt

from utils import create_meshes, create_surface, form_side_surfaces

def circle_points_through_A(A, segments=16):
    A = Vector(A)
    O = Vector((0, 0, A.z))
    r_vec = A - O
    radius = r_vec.length

    U = r_vec.normalized()
    V = Vector((0, 0, 1)).cross(U).normalized()

    points = []
    for i in range(segments):
        angle = 2 * pi * i / segments
        point = O + radius * (cos(angle) * U + sin(angle) * V)
        points.append(point)
    return points

def create_points_around_axis(base_point: Vector, axis_dir: Vector, segments: int=32):
    A = Vector(base_point)
    axis = Vector(axis_dir).normalized()

    # Project A onto the axis to find the center
    center = axis * A.dot(axis)

    # Vector from center to A = radius vector
    r_vec = A - center
    radius = r_vec.length
    if radius == 0:
        raise ValueError("Point A lies on the axis — cannot define unique circle.")

    # Orthonormal basis in the perpendicular plane
    U = r_vec.normalized()
    V = axis.cross(U).normalized()

    # Generate circle points
    points = []
    for i in range(segments):
        theta = 2 * pi * i / segments
        point = center + radius * (cos(theta) * U + sin(theta) * V)
        points.append(point)

    return points

def test_circle(bm):
    # try a random A 
    A = Vector((0, 3, 5))
    # try creating Oz circle point via 1st fn (fixed)
    Oz_circle_coords = circle_points_through_A(A)
    Oz_circle_points = [bm.verts.new(p) for p in Oz_circle_coords]
    bm.faces.new(Oz_circle_points)
    # try creating Oy circle point via 2nd fn (arbitrary)
    Oy_circle_coords = create_points_around_axis(A, (0, 1, 0))
    Oy_circle_points = [bm.verts.new(p) for p in Oy_circle_coords]
    bm.faces.new(Oy_circle_points)
    return bm 

def create_point_projection(center: tuple, curve: list, radius: float, projection_region: tuple):
    """Attempt to project a list of points as curve into a same direction cylinder-ish surface. Curve should be height x width with 0-1 form and will span `projection_region` rad.
    Can and maybe should be use to project everything 
    """
    height, apply_region_rad = projection_region 
    cx, cy, cz = center
    
    def to_angle(x):
        # should stretch x's 0-1 to angle 
        return x * apply_region_rad
    coords_3d = []
    for x, y in curve:
        theta = to_angle(x)
        # projection will have x constitute the X/Z coordinate and y constitute the Y 
        Xp = cx + sin(theta) * radius
        Yp = cy + cos(theta) * radius
        Zp = cz + y          * height
        coords_3d.append((Xp, Yp, Zp))
    
    return coords_3d

# actual handling of the helmet. There should be 3 parts in general 
# contact point, which is the under/inside of the helmet; should house the stud appropriately.
# top, which is the dome/tip/whatever shape on top 
# side, which are the walls going down into the chin.

head_diameter = 10.2
main_head_height = 8.5
stud_diameter = 4.8
stud_height = 1.7

default_head_radius = head_diameter / 2 + 0.1
default_stud_radius = stud_diameter / 2
default_stud_height = stud_height + 0.1 # clearance 
default_wall_thickness = 1.0

def form_contact_point_profile(center=(0, 0, 0),
        head_radius=default_head_radius,    # true LEGO head radius, now accounted for fit clearance
        stud_radius=default_stud_radius,    # LEGO stud radius
        stud_height=default_stud_height,    # LEGO stud height
        fit_clearance=0.1, # fit clearance to account for shrinkage etc, used mostly to allow space for head
        curve_clearance=0.15,  # internal/external curves to allow strongger connection/form
        segments=32
    ):
    # prepare values and starter point
    center = Vector(center)
    angle_perc = pi * 2 / segments
    true_center = center + Vector((0, 0, stud_height))
    
    # construct the series of points that would then be mirrored to form the actual contact point of the helm.
    # top outer edge of the stud
    stud_top_edge = true_center + Vector((0, stud_radius, 0))
    points = []
    # forming a curve of curve_clearance height 
    for i in range(segments // 4): # run on pi/2; hence segments/4
        angle = angle_perc * i
        points.append(stud_top_edge + Vector( (0, curve_clearance * (-1+sin(angle)), curve_clearance * (-1+cos(angle)) ) ))
    # continue down to bottom edge and form the curve again. For now also add fit_clearance to ensure stud can be fit in regardless
    stud_bottom_edge = stud_top_edge + Vector((0, fit_clearance, -stud_height))
    for i in range(segments // 4):
        angle = angle_perc * i 
        points.append(stud_bottom_edge + Vector( (0, curve_clearance * (1-cos(angle)), curve_clearance * (1-sin(angle)) ) ))
    # expand from this bottom edge and prepare supports for inevitable walling. Since above already have fit_clearance, no need to add more. TODO just set its y to head_radius + fit_clearance directly?
    stud_internal_edge = stud_bottom_edge + Vector((0, head_radius - stud_radius, 0))
    for i in range(segments // 4): # run on pi/2; hence segments/4
        angle = angle_perc * i
        points.append(stud_internal_edge + Vector( (0, curve_clearance * (-1+sin(angle)), curve_clearance * (-1+cos(angle)) ) ))
    
    return points 

def form_rounded_top_profile(center=(0, 0, 0), height=6.0, radius=default_head_radius+default_wall_thickness, ignore_center_point=True, segments=32):
    """Form a simple rounded top using similar mechanism as the oval blade."""
    points = []
    center = Vector(center)
    angle_perc = pi * 2 / segments
    for i in range(segments // 4):
        if i==0 and ignore_center_point:
            continue 
        angle = angle_perc * i
        points.append(center + Vector((0, radius * cos(angle), height * sin(angle))))
    return points 

def form_short_side_profile(center=(0, 0, 0), internal_radius=default_head_radius, external_radius=default_head_radius+default_wall_thickness, height=1.8):
    """Form short (near eyebrow) covering; this cutoff across all front."""
    center = Vector(center)
    internal_top = center + Vector((0, internal_radius, 0))
    internal_bottom = internal_top + Vector((0, 0, -height))
    external_bottom = internal_bottom + Vector((0, external_radius - internal_radius, 0))
    external_top = external_bottom + Vector((0, 0, height))
    # actually just keep the internal/external bottom; since top should already been changed 
    return [internal_bottom, external_bottom]

def form_faced_side_points(center=(0, 0, 0), internal_radius=default_head_radius, external_radius=default_head_radius+default_wall_thickness, height=main_head_height, face_height=main_head_height*0.9, axis_dir=(0, 0, 1), segments=32, face_segments=(0.25, 0.25)):
    """Form the complete covering head, with opener cut out for faces. Crude version by simply lifting relevant vertices up on a sinoid pattern"""
    center = Vector(center)
    internal_bottom = center + Vector((0, internal_radius, -height))
    external_bottom = internal_bottom + Vector((0, external_radius - internal_radius, 0))
    internal_points, external_points = [create_points_around_axis(p, axis_dir, segments=segments) for p in [internal_bottom, external_bottom]]
    # perform raising for -segment//8 -> segment//8, along +y aligmnent 
    # nvm. Perform raising for additional segment // 8 in the middle
    center_size = segments // 16
    side_size = segments // 8
    angle_perc = pi / (side_size*2) # will use sin to go 0->1->0
    for i in range(side_size * 2 + center_size + 1):
        point_index = (i - (side_size * 2 + center_size))
        if side_size < i < side_size + center_size:
            angle_index = None
            increment_vector = Vector((0, 0, face_height))
        elif side_size >= i:
            angle_index = i
            increment_vector = Vector((0, 0, face_height * sin(angle_perc * angle_index)))
        else: # i >= side_size + center_size
            angle_index = i - center_size
            increment_vector = Vector((0, 0, face_height * sin(angle_perc * angle_index)))
        # print(i, angle_index, increment_vector)
        internal_points[point_index] = internal_points[point_index] + increment_vector
        external_points[point_index] = external_points[point_index] + increment_vector
    return [internal_points, external_points]

def form_faced_side(bm, inner_rim_vertices, outer_rim_vertices, axis_dir=(0, 0, 1), **kwargs):
    """The above except converting to actual vertices and forming the faces with the inner_rim_vertices/outer_rim_vertices"""
    vector_points = form_faced_side_points(axis_dir=axis_dir, **kwargs)
    all_points = [inner_rim_vertices] + [[bm.verts.new(p) for p in ps] for ps in vector_points] + [outer_rim_vertices] # points in bm vert 
    form_side_surfaces(bm, all_points)
    return bm
    
cheap_sqrt_2 = sqrt(2)

def form_cutout(segments=32, cheek_ratio=4, ingress_size=2):
    """Form a direct cutout to apply on the face via create_point_projection. Need to do manually to keep better control.
    not sure what's the correct word for pressing inside. Using `ingress` for now. Refactor later."""
    # center is 0, 0; radius is 1 
    radius = 1 
    cx = radius / cheap_sqrt_2 
    cy = - cx
    angle_perc = pi * 2 / segments 
    positive_points = []
    for i in range(segments // 8, segments - ingress_size * segments // 8):
        angle = angle_perc * i - pi / 2
        positive_points.append((cx + sin(angle) * radius, cy + cos(angle) *  radius))
    # form the relevant underside. Cheek will lose 1/sqrt_2 height, so it's recommended to give extra. Will span up to y limit of the circle, so this need to take 45+90 deg
    underside = []
    for i in range(ingress_size * segments // 8):
        tx, ty = positive_points[-(i+1)]
        underside.append((tx, -cheek_ratio * radius))
    curve_forward = positive_points + underside 
    # mirror and use the center 0, 0 as middle 
    curve_backward = [(-x, y) for x, y in curve_forward[::-1]]
    curve = curve_backward[:-1] + [(0, 0)] + curve_forward[1:]
    # normalize down to [0, 1] range 
    xs, ys = zip(*curve); lx, ly = min(xs), min(ys)
    xs, ys = zip(*curve); hx, hy = max(xs), max(ys)
    dx, dy = hx - lx, hy - ly
    normalized_curve = [((x-lx)/dx, (y-ly)/dy) for x, y in curve] 
    # return both the curve and the last paired segment set to form faces and deduce
    return normalized_curve, ingress_size * segments // 8

def form_cutout_connectable(bm, inner_rim_vertices, outer_rim_vertices, center=(0, 0, 0), internal_radius=default_head_radius, external_radius=default_head_radius+default_wall_thickness, height=main_head_height, face_height=main_head_height*0.9, axis_dir=(0, 0, 1), segments=32):
    """Try to form only the projected cutout first."""
    center = Vector(center)
    curve, ingress = form_cutout(segments=segments)
    bottom_center = center + Vector((0, 0, -height))
    # set up the external curve on the positive side 
    external_curve = create_point_projection(bottom_center, curve, external_radius, (face_height, pi / 2))
    internal_curve = create_point_projection(bottom_center, curve, internal_radius, (face_height, pi / 2))
    external_curve_points = [bm.verts.new(p) for p in external_curve]
    internal_curve_points = [bm.verts.new(p) for p in internal_curve]
    bm.verts.ensure_lookup_table()
#    for i in range(len(internal_curve_points) - 1):
#        bm.faces.new([internal_curve_points[i], internal_curve_points[i+1], external_curve_points[i+1], external_curve_points[i]])

    # forming the 2nd set of points forming the remaining walls 
    internal_bottom = center + Vector((0, internal_radius, -height))
    external_bottom = internal_bottom + Vector((0, external_radius - internal_radius, 0))
    internal_raw, external_raw = [create_points_around_axis(p, axis_dir, segments=segments) for p in [internal_bottom, external_bottom]]
    internal_points = [bm.verts.new(p) for p in internal_raw][:segments - segments // 4 + 1]
    external_points = [bm.verts.new(p) for p in external_raw][:segments - segments // 4 + 1]

    bm.verts.ensure_lookup_table()
    # underneath surface go through all points
    ai_points = internal_points + internal_curve_points[::-1] 
    ae_points = external_points + external_curve_points[::-1]
    form_side_surfaces(bm, [ai_points, ae_points])
    # actual surface require to form separate cheek sections first. 
    # TODO also ensure triangle face on non-divisible surfaces.
    for cheek_sections in [internal_curve_points, external_curve_points]:
        left_section = cheek_sections[:ingress]
        right_section = cheek_sections[ingress:ingress*2][::-1]
        for i in range(len(left_section) - 1):
            bm.faces.new([left_section[i], left_section[i+1], right_section[i+1], right_section[i]])
        left_section = cheek_sections[-ingress:]
        right_section = cheek_sections[-ingress*2:-ingress][::-1]
        for i in range(len(left_section) - 1):
            bm.faces.new([left_section[i], left_section[i+1], right_section[i+1], right_section[i]])

    # form the remaining regions side by both the manual 1-1 and create_surface
    for i in range(len(internal_points) - 1):
        bm.faces.new([internal_points[i], internal_points[i+1], inner_rim_vertices[i+1], inner_rim_vertices[i]])
        bm.faces.new([external_points[i], external_points[i+1], outer_rim_vertices[i+1], outer_rim_vertices[i]])
    create_surface(bm, external_curve_points[ingress*2:-ingress*2], outer_rim_vertices[len(internal_points)-1:] + outer_rim_vertices[:1], form_complete_surface=False, is_parallel=True)
    create_surface(bm, internal_curve_points[ingress*2:-ingress*2], inner_rim_vertices[len(internal_points)-1:] + inner_rim_vertices[:1], form_complete_surface=False, is_parallel=True)
#    cheek_regions = [internal_curve_points[:]]
#    for i in range(0, segments - segments // 4):
#        bm.faces.new([internal_points[i], internal_points[i+1], external_points[i+1], external_points[i]])

#    create_surface(bm, internal_curve_points, external_curve_points)
    return bm
    

def form_advanced_side_points(center=(0, 0, 0), internal_radius=default_head_radius, external_radius=default_head_radius+default_wall_thickness, height=main_head_height, face_height=main_head_height*0.9, axis_dir=(0, 0, 1), segments=32):
    """Simple version doesnt work. This version should (1) has rimmed edges and (2) enhanced (better resolution) side profile. Only leaves the same contact points as the original to make sure join up can work"""
    center = Vector(center)
    internal_bottom = center + Vector((0, internal_radius, -height))
    external_bottom = internal_bottom + Vector((0, external_radius - internal_radius, 0))
    internal_points, external_points = [create_points_around_axis(p, axis_dir, segments=segments) for p in [internal_bottom, external_bottom]]
    # form the relevant face-cutout 
    # form the original curve on the face cutout - 1/2 circle for eye socket, flat downward for breathing.
    curve = []
    r = visor_radius = default_head_radius * 0.2
    ecx, ecy = r / cheap_sqrt_2, 3 * r # center of the eye
    angle_perc = pi * 2 / segments
    for i in range(segments // 2):
        angle = angle_perc * (i+1) - pi / 4
        point = px, py = ecx + r * sin(angle), ecy + r * cos(angle)
        curve.append(point)
    # after this, move downward and apply for the faceplate 
    lx, ly = curve[-1]
    # rescale points to their maximum height & span 
    widths, heights = zip(*curve)
    max_width, max_height = max(widths), max(heights)
    normalized_curve = [(px / max_width, py / max_height) for px, py in curve]
    # add the last point at the edge of the projection
    normalized_curve.append((1.0, 0.0))
    bottom_center = center + Vector((0, 0, -height))
    # set up the external curve on the positive side 
    external_curve_pside = create_point_projection(bottom_center, normalized_curve, external_radius, (face_height, pi / 4))
    # append the negative side by inverting the y point coordinate 
    external_curve_nside = [(-x, y, z) for x, y, z in external_curve_pside[1:]][::-1]
#    external_curve = external_curve_nside + external_curve_pside
    internal_curve_pside = create_point_projection(bottom_center, normalized_curve, internal_radius, (face_height, pi / 4))
    # append the negative side by inverting the y point coordinate 
    internal_curve_nside = [(-x, y, z) for x, y, z in internal_curve_pside[1:]][::-1]
    #print(internal_curve_nside, internal_curve_pside)
#    internal_curve = internal_curve_nside + internal_curve_pside
    # the curves has a face between the last 1/4 arc and the below plate; make sure to take care of that before joining
    expanded_internal_points = internal_curve_nside[::-1] + internal_points[segments//4:-segments//4] + internal_curve_pside[::-1]
    expanded_external_points = external_curve_nside[::-1] + external_points[segments//4:-segments//4] + external_curve_pside[::-1]
    return expanded_internal_points, expanded_external_points
    
def form_advanced_side(bm, inner_rim_vertices, outer_rim_vertices, axis_dir=(0, 0, 1), segments=32, **kwargs):
    # retrieve the points first 
    inner_bottom_raw_points, outer_bottom_raw_points = form_advanced_side_points(axis_dir=axis_dir, segments=segments, **kwargs)
    inner_bottom_vertices = [bm.verts.new(p) for p in inner_bottom_raw_points]
    outer_bottom_vertices = [bm.verts.new(p) for p in outer_bottom_raw_points]
    # custom form the faces. Extract the connection between the end of the eye-tip and the end of the faceplate underside.
    prs, pre = (segments // 2 - segments // 8), (segments // 2 + 2) # positive_region_start, positive_region_end
    internal_region_1 = inner_bottom_vertices[prs:pre]
    external_region_1 = outer_bottom_vertices[prs:pre]
    # extract the same region for the mirrored side 
    internal_region_2 = inner_bottom_vertices[::-1][prs-1:pre-1]
    external_region_2 = outer_bottom_vertices[::-1][prs-1:pre-1]
    # the regions should have the same count and structure, so face forming should work 
    bm.verts.ensure_lookup_table()
    for region in [internal_region_1, internal_region_2, external_region_1, external_region_2]:
        bottom_vertex_1, bottom_vertex_2 = region[-2:]
        bm.faces.new([bottom_vertex_1, bottom_vertex_2, region[0]])
        for p1, p2 in zip(region[:-3], region[1:-2]):
            bm.faces.new([p1, p2, bottom_vertex_2])
    # once the custom are built, link up using generic create_surface 
    form_side_surfaces(bm, [inner_bottom_vertices, outer_bottom_vertices])
    linkup_inner_vertices = inner_bottom_vertices[:prs+1] + inner_bottom_vertices[pre-1:-pre] + inner_bottom_vertices[-prs:]
    linkup_outer_vertices = outer_bottom_vertices[:prs+1] + outer_bottom_vertices[pre-1:-pre] + outer_bottom_vertices[-prs:]
    create_surface(bm, inner_rim_vertices, linkup_inner_vertices)
    create_surface(bm, outer_rim_vertices, linkup_outer_vertices)
    return bm


def form_contact_point(bm, profile_fn=form_contact_point_profile, axis_dir=(0, 0, 1), segments=32, **kwargs):
    """Default to form_contact_point_profile; this form the actual sealed surface where the head stud would be connected. Return the contact surface points (the internal-top of the side wall)."""
    profile_points = profile_fn(**kwargs)
    all_points = [create_points_around_axis(p, axis_dir, segments=segments) for p in profile_points]
    all_bm_points = [[bm.verts.new(p) for p in ps] for ps in all_points] # points in bm vert 
     # form the side walls from the vertices
    form_side_surfaces(bm, all_bm_points)
    # cap top, return bottom
    bm.faces.new(all_bm_points[0])
    return bm, all_bm_points[-1]

def form_top(bm, profile_fn=form_rounded_top_profile, axis_dir=(0, 0, 1), segments=32, **kwargs):
    # pretty much the same as form_contact_point in practice; but capping bottom (tip) instead.
    profile_points = profile_fn(**kwargs)
    all_points = [create_points_around_axis(p, axis_dir, segments=segments) for p in profile_points]
    all_bm_points = [[bm.verts.new(p) for p in ps] for ps in all_points] # points in bm vert 
     # form the side walls from the vertices
    form_side_surfaces(bm, all_bm_points)
    # cap bottom and return top instead as the profile is inverted (going from rim to tip)
    bm.faces.new(all_bm_points[-1])
    return bm, all_bm_points[0]


def test_hat_contact(bm):
    # form the contact hat. This only form a complete rounded version now. 
    bm, outer_rim_vertices = form_top(bm)
    bm, inner_rim_vertices = form_contact_point(bm)
    bm = form_faced_side(bm, inner_rim_vertices, outer_rim_vertices)
    return bm 

def test_hat_projected(bm):
    # form the helm with the projected cutout. 
    bm, outer_rim_vertices = form_top(bm)
    bm, inner_rim_vertices = form_contact_point(bm)
    bm = form_cutout_connectable(bm, inner_rim_vertices, outer_rim_vertices)
    return bm 
