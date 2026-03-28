"""Building compatible barrels for various machine gun or artillery. This should also contains muzzle logic whenever available.
Due to connectors being bar (for MG barrels) and stud (for cannons), this shouldn't need to have specific peg shapes.

For flat (reorganized now, assuming no offset involved):
x_lower_edges is the edge paralleling x axis direction with the smallest x
x_upper_edges is the opposite edge (also parallel x axis, biggest x)
y following the same rule.
"""

from math import sin, cos, pi 
from mathutils import Vector
import bmesh

import json

from utils import create_cylinder
from utils import SEGMENTS, BAR_DIAMETER, STUD_DIAMETER, STUD_HEIGHT


HMG_BARREL_DIAMETER = BAR_DIAMETER * 1.2
HMG_BARREL_RADIUS = HMG_BARREL_DIAMETER /  2

def generate_quarter_indent(bm=None, offset: callable=None, segments=8):
    """This simply generate a flat 1 unit half indent from the Oxy `flat` surface.
    Step 1 of generating the sleeve regions. This is the minimal variant that we'll clone to form appropriate sections.
    This will generate the points list that are _DIAGONAL_ to the Ox/Oy directions. Supplying bm will give the true edge vertices.
    Can supply an offset, preferably a callable; but a tuple can also work.

    This should result in a 1x1 section.
    """
    if offset:
        if not callable(offset):
            ox, oy, oz = offset 
            offset = lambda p: (ox+p[0], oy+p[1], oz+p[2])
    # start with the indent region
    bottom_point = [1, 1, -1] # center of the indent, 
    points = [[bottom_point]]
    for depth_index in range(1, segments+1):
        depth_points = []
        depth_angle = pi / 2 * depth_index / segments
        z = depth = -cos(depth_angle) # this is the z value for the entire rim (swing)
        swing_distance = sin(depth_angle) # this is the radius of the rim
        for swing_index in range(segments+1):
            # this is iterating along the 'rim' of the indent. It radiates from the bottom_point (1, 1), so it need to reduce via the swing_distance 
            # TODO should have segments+1 here?
            swing_angle = pi / 2 * swing_index / segments
            delta_x = cos(swing_angle) * swing_distance
            x = 1 - delta_x
            delta_y = sin(swing_angle) * swing_distance
            y = 1 - delta_y 
            # add in the point to the rim unit
            depth_points.append([x, y, z])
        # join the rim units to full points 
        points.append(depth_points)
    # append the starting point 
    start_point = [0, 0, 0]
    points.append([start_point])
    
    if offset:
        assert callable(offset), f"@generate_indent_points: offset supplied need to callable or converted to such; instead is {offset}"
        offseted_points = [[offset(p) for p in ps] for ps in points]
        points = offseted_points

    if bm:
        # try the version with immediate face generation.
        # turn out we can just clear out duplicate vertices when done, this might not need all the jazz of creating faces AFTER the construction.
        vertices = []
        for ps in points:
            vertices.append([bm.verts.new(p) for p in ps])
        bm.verts.ensure_lookup_table()
        # build the faces between the layers.
        for sps, nps in zip(vertices[:-1], vertices[1:]): # start_points, next_points
            if len(sps) == 1 or len(nps) == 1:
                # this is linked toward a single vertex
                # create a singular face from all points 
                bm.faces.new(sps + nps)
                continue 
            # this is linking between two list of vertices. Should be EXACTLY matching
            assert len(sps) == len(nps), f"Invalid list pairing: {sps}, {nps}"
            for i in range(len(sps)-1):
                bm.faces.new([sps[i], sps[i+1], nps[i+1], nps[i]])
        # after this, only keep the outward facing vertices 
        # keep in the form of [x_lower, x_upper, y_lower, y_upper]. All vertices should go in _increasing_ direction (eg 0->0.2->1 assuming no offset)
        start_vertex = vertices[-1][0]
        bottom_vertex = vertices[0][0]
        topmost_y_vertex, topmost_x_vertex = vertices[-2][-1], vertices[-2][0]
        # lower edges are *flat* one, so only have several lines
        x_lower_edges = [start_vertex, topmost_y_vertex]
        y_lower_edges = [start_vertex, topmost_x_vertex]
        # upper edges are the curved undersides; they are all generated tipmost points (so 0/-1 and excluding the start vertices)
        x_upper_edges = [ps[0] for ps in vertices[:-1]][::-1]
        y_upper_edges = [ps[-1] for ps in vertices[:-1]][::-1]

        #print("x_lower_edges"), printv(x_lower_edges)
        #print("x_upper_edges"), printv(x_upper_edges)
        #print("y_lower_edges"), printv(y_lower_edges)
        #print("y_upper_edges"), printv(y_upper_edges)
        return x_lower_edges, x_upper_edges, y_lower_edges, y_upper_edges
    else:
        return points

printv = lambda ls: print([" ".join([f"{p:.2f}" for p in v.co]) for v in ls])

def print_debug(local):
    """TODO put the code to read and print via locals the various edge info."""
    for key in ["xle1", "xue1", "yle1", "yue1",
                "xle2", "xue2", "yle2", "yue2",
                "x_lower_edges", "x_upper_edges", "y_lower_edges", "y_upper_edges"
                ]:
        if key in local:
            print(key)
            printv(local[key])

def generate_half_indent(bm, offset: callable=None):
    """
    Step 2.1 of the sleeve generation. TODO standardized for mirroring?
    Flip the quadrant unit directly on the y axis.

    This should result in a 1x2 section
    """
    offset = offset or (lambda x: x) # TODO clean this later.
    xle1, xue1, yle1, yue1 = generate_quarter_indent(bm, offset=offset)
    invert_offset = lambda p: offset((p[0], -p[1]+2, p[2]))
    xle2, xue2, yle2, yue2 = generate_quarter_indent(bm, offset=invert_offset)
    # x upper should match exactly to each other
    # print("Should match: ", [v.co for v in xue1], "vs", [v.co for v in xue2], [v1.co == v2.co for v1, v2 in zip(xue1, xue2)])
    # above is confirmed. Reform into new edge sections.
    x_lower_edges = xle1
    x_upper_edges = xle2 # (lowers from invert section became upper of the total) 
    y_lower_edges = yle1 + yle2[:-1] # join the flat side edges together.
    y_upper_edges = yue1[:-1] + yue2[::-1] # is actually listed backward now as it start with yue1 topmost_y_vertex and ends with yue2 topmost_y_vertex. Still, since we are joining them immediately this shouldn't be a big deal.
    # return the joined version to try for now 
    return x_lower_edges, x_upper_edges, y_lower_edges, y_upper_edges

def generate_full_indent(bm, offset: callable=None, indent_distance: float=4):
    """Step 2.2 of the sleeve generation. Should result in a full elongated indent that can be further cloned and then projected.
    Flip and move away a distance on the x axis 
    
    This should generate a 6x2 section
    """
    offset = offset or (lambda x: x) # TODO clean this later.
    xle1, xue1, yle1, yue1 = generate_half_indent(bm, offset=offset)
    indent_size = indent_distance + 2*1 # length of the whole indent section; the quarters are always in size 1
    invert_offset = lambda p: offset((-p[0]+indent_size, p[1], p[2]))
    xle2, xue2, yle2, yue2 = generate_half_indent(bm, offset=invert_offset)
    # now y upper will NOT match exactly, instead they should be joined together 
    #print("Should have same y/z: ", [v.co for v in yue1], "vs", [v.co for v in yue2])
    for vs in zip(yue1[:-1], yue1[1:], yue2[1:], yue2[:-1]):
        # print([v.co for v in vs])
        bm.faces.new(vs)
    # Join up the edges. See half indent above for methodology.
    x_lower_edges = xle1 + xle2[::-1] # since faces are being joined instead of removed; we keep all vertices joined together
    x_upper_edges = xue1 + xue2[::-1]

    y_lower_edges = yle1
    y_upper_edges = yle2


    #print_debug(locals())
    return x_lower_edges, x_upper_edges, y_lower_edges, y_upper_edges

def generate_sleeve_flat_section(bm, offset=None, indent_distance: float=4):
    """Step 3.1 of the sleeve generation. Generate the 4x2 section of the sleeve, in flattened mode.
    Essentially create and join the indented sections together. Due to this construction method, the sleeves only have 4x4=16 resolution. Can add additional point later inbetween the quarter to ensure proper segmentation.

    This should generate a 6x16 section equivalent a whole cylindrical segment.
    """
    offset = offset or (lambda x: x) # TODO clean this later.
    # indent are laid sideway (y direction)
    indents = [generate_full_indent(bm, offset=lambda p: offset((p[0], p[1] + 4*i, p[2])), indent_distance=indent_distance) for i in range(4)]
    # expand all these indent to 2 units and linking them together  
    start_edges, end_edges = [], [] # x_lower_edges/x_upper_edges of the whole section. Will be useful after deformation joins
    for i, indent_edges in enumerate(indents):
        # y_upper_edges of i -> y_lower_edges of i+1; or new points if they doesn't match 
        x_lower_edges, x_upper_edges, y_lower_edges, y_upper_edges = indent_edges
        lower_points = x_upper_edges 
        # print(lower_points)
        middle_points = [bm.verts.new((p.co[0], p.co[1]+1, p.co[2])) for p in lower_points] # TODO just vector plus this instead?
        # add to the relevant edges before, so upper_points can be added only when they actually being created.
        start_edges.extend(y_lower_edges); start_edges.append(middle_points[0])
        end_edges.extend(y_upper_edges); end_edges.append(middle_points[-1])
        if i+1 < len(indents): # has valid top, use that.
            upper_points, _, _, _ = indents[i+1] 
        else:
            upper_points = [bm.verts.new((p.co[0], p.co[1]+1, p.co[2])) for p in middle_points]
            # add the newly created points too.
            start_edges.append(upper_points[0])
            end_edges.append(upper_points[-1])
        # create faces 
        bm.verts.ensure_lookup_table()
        #printv(lower_points); printv(middle_points); printv(upper_points)
        for i in range(len(lower_points)-1):
            bm.faces.new((lower_points[i], lower_points[i+1], middle_points[i+1], middle_points[i]))
            bm.faces.new((middle_points[i+1], middle_points[i], upper_points[i], upper_points[i+1]))

    return start_edges, end_edges

def generate_sleeve_flat(bm, section_count: int=2, section_indent_count: int=3, section_distance: float=2, section_indent_distance: float=1, indent_distance: float=4):
    """Step 3.2: generate repeating sections forward to form the full sleeve.
    This will try to create {section_count} bundle of close indents ({section_indent_count} indents distanced by {section_indent_distance}) which are further with {section_distance} _over_ the section_indent_distance

    ~~Should be a 41x6 section - pair of 3x sleeve sections joined at 3 (6x3+1)x2+3. This should be ready to join the bar and flash hider in its final configuration.~~
    """
    current_last_edges = None 
    true_start_edges = true_end_edges = None 
    indent_true_size = indent_distance + 2*1 + section_indent_distance
    extra_distance_per_sections = section_distance
    for i in range(section_count * section_indent_count):
        section = i // section_indent_count 
        extra_distance = section * extra_distance_per_sections
        # first section - 3x the generate_sleeve_flat_section  
        # actually stamp the 2nd section here with the 2. Cant be arsed to fix it now
        offset = lambda p: (p[0]+ i * indent_true_size + extra_distance, p[1], p[2])
        section_start_edges, section_end_edges = generate_sleeve_flat_section(bm, offset=offset, indent_distance=indent_distance)
        if i == 0:
            true_start_edges = section_start_edges # 1st section, its start edge is the actual starting edge of the whole sleeve.
        else:
            # 2+ section, join up with previous data 
            for s1, s2, e1, e2 in zip(current_last_edges[:-1], current_last_edges[1:], section_start_edges[:-1], section_start_edges[1:]):
                bm.faces.new((s1, s2, e2, e1))
        # record the final edge of the section 
        current_last_edges = section_end_edges 
    true_end_edges = current_last_edges
    return true_start_edges, true_end_edges

def generate_full_sleeve(bm, edges, raise_size: float=1, wall_size: float=1, connection_size: float=4, connection_length: float=6, connection_is_intrusion=True):
    """Step 3.3: Generate the connection section for the sleeve. Need to supply 
    - The start/end edges to protrude from
    - The ratio of wall-to-indent for the bar insertion (2 to 4 atm)
    ~~Connection will be a depression of 2x bar diameter (4x2x2=16). Don't mind if it's too high; the flattened version is NOT up to scale.~~ Connection length is following length side and cannot be really gauged.
    This will then form a bar-compatible connection at the start and a flash-hider at the end. If connection_is_intrusion (default); the connection will be a hole (intrusion) and if not it'll be a bar (extrusion)
    """
    start_edges, end_edges = edges 

    def offset_and_form_faces(points, offset: Vector):
        new_points = [bm.verts.new(v.co + offset) for v in points]
        bm.verts.ensure_lookup_table()
        for s1, s2, e1, e2 in zip(points[:-1], points[1:], new_points[:-1], new_points[1:]):
            bm.faces.new((s1, s2, e2, e1))
        return new_points
    # perform the following for the start section:
    # - raise the face by {raise_size}z and -1x; this add extra reinforcement and start the base of the connection 
    # - if intrusion:
    #   - extend this face by -{connection_length}x unit
    #   - form the wall by -{raise_size}-{wall_size}z and then +{connection_length}x 
    #   - form the inside of the connection by -{connection_size}z; all these points will be synced to one point when done.
    # - if extrusion:
    #   - lower the face from this reinforcement by -{raise_size}-{wall_size}z again to find the base. TODO make a reinforced bevel?
    #    - extend out by -{connection_length}x and cap off by -{connection_size}z to form the extrusion bar.
    if connection_is_intrusion: 
        start_offsets = [Vector((-1, 0, raise_size)), Vector((-connection_length, 0, 0)), Vector((0, 0, -wall_size-raise_size)), Vector((connection_length, 0, 0)), Vector((0, 0, -connection_size))]
    else:
        start_offsets = [Vector((-1, 0, raise_size)), Vector((0, 0, -wall_size-raise_size)), Vector((-connection_length, 0, 0)), Vector((0, 0, -connection_size))]
    current_points = start_edges 
    for offset in start_offsets:
        current_points = offset_and_form_faces(current_points, offset)
    new_start_edges = current_points # should be the exact same points after wrapping
    
    # perform the following for the end section:
    # - raise the face by 0.5z and then 4x forward (forming a 2/3 of the groove) pronounced section 
    # - lower -2.5z and then +6x 2z to form the flash hider at roughly the same diagonal form 
    # - lower 6z for the final section
    current_points = end_edges
    for offset in [Vector((0.5, 0, 0)), Vector((0, 0, raise_size)), Vector((3.5, 0, 0)), Vector((0, 0, -wall_size-raise_size)), Vector((6, 0, wall_size)), Vector((0, 0, -wall_size-connection_size))]:
        current_points = offset_and_form_faces(current_points, offset)
    new_start_edges = end_edges # should be the exact same points after wrapping

def generate_sleeve_wrapped(bm, wall_size=1, connection_size=4, raise_size=1, connection_length=6, connection_is_intrusion=True, **kwargs):
    """Step 4. Convert the entire mesh into x-axis rolling. """
    edges = generate_sleeve_flat(bm, **kwargs)
    generate_full_sleeve(bm, edges, wall_size=wall_size, connection_size=connection_size, raise_size=raise_size, connection_length=connection_length, connection_is_intrusion=connection_is_intrusion)
    # targets all vertices and convert them. x is kept the same; y-z become angle and radius respectively.
    # z convert to radius with -6 = 0; -2 = 1/2bar radius (4 = HMG_BARREL_RADIUS)
    barrel_radius = wall_size + connection_size
    def convert_to_wrap(vertex):
        fx, fy, fz = vertex.co 
        point_radius = (fz+barrel_radius) / 4 * HMG_BARREL_RADIUS
        point_angle = fy * pi/8
        nx = fx 
        ny = sin(point_angle) * point_radius 
        nz = -cos(point_angle) * point_radius
        vertex.co = (nx, ny, nz)
    for v in bm.verts:
        convert_to_wrap(v)

def test_indent_region(bm, version=-1):
    """test the above indent thing. Can remove if later sufficiently documented.
    Right now user can input version 0 -> 5 to get the steps operated to get the final results.
    """
    available_tests = [generate_quarter_indent, generate_half_indent, generate_full_indent, generate_sleeve_flat_section, generate_full_sleeve, generate_sleeve_wrapped]
    if isinstance(version, int):
        function = available_tests[version]
    vertices = function(bm)
    
    return bm

    
