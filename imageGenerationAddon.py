bl_info = {
    "name": "Image Generation Addon for ML",
    "description": "",
    "author": "Tilen Sketa",
    "version": (2, 0, 0),
    "blender": (3, 0, 1),
    "location": "3D View > Tools",
    "warning": "", # used for warning icon and text in addons panel
    "wiki_url": "",
    "tracker_url": "",
    "category": "Development"
}

import bpy
import math
import os
import random
import sys

from bpy.props import (StringProperty,
                       IntProperty,
                       FloatProperty,
                       PointerProperty,
                       )
from bpy.types import (Panel,
                       Operator,
                       PropertyGroup,
                       )

def update_environment_strength(self, context):
    """Update environmet texture strength"""
    bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[1].default_value = self.environment_strength

def update_max_offset(self, context):
    scene = bpy.context.scene
    offset_circle = scene.objects["Offset"]
    if not offset_circle:
        offset_circle = bpy.ops.mesh.primitive_circle_add(
            size=2, 
            enter_editmode=False, 
            align='WORLD', 
            location=(0, 0, 0), 
            scale=(1, 1, 1))

        # Make planes name ShadowCatcher
        bpy.context.object.name = "Offset"
        # Set scene visibility
        offset_circle.hide_render = True
    offset_circle.scale = (self.max_offset, self.max_offset, self.max_offset)


# ------------------------------------------------------------------------
#    Scene Properties
# ------------------------------------------------------------------------

class MyProperties(PropertyGroup):
    
    environment_strength: FloatProperty(
        name = "Environment Light Strength",
        default = 1,
        min = 0,
        max = 2,
        update = update_environment_strength,
        step = 1
        )
        
    number_of_images: IntProperty(
        name = "Number Of Images",
        default = 1,
        min = 1,
        max = 1000000
        )

    image_offset: IntProperty(
            name = "Image offset",
            default = 0,
            min = 0,
            max = 1000000
        )

    max_offset: FloatProperty(
        name = "Max offset from center",
        default = 0,
        min = 0,
        max = 10,
        update = update_max_offset,
        step = 1
        )

    output_path: StringProperty(
        name = "Output",
        default="",
        subtype='FILE_PATH'
        )
        
    my_collection : PointerProperty(
        name="Collection",
        type=bpy.types.Collection
        )

# ------------------------------------------------------------------------
#    Functions
# ------------------------------------------------------------------------

def is_child(obj):
    return obj.parent is not None

def setup_output_folder():
    """Setup output folder with subfolders black and images"""
    mytool = bpy.context.scene.my_tool
    black_folder = mytool.output_path + "black"
    images_folder = mytool.output_path + "images"
    if not os.path.exists(black_folder):
        os.mkdir(black_folder)
    if not os.path.exists(images_folder):
        os.mkdir(images_folder)

def verify_collection():
    """Verify collection and if collection is empty raise error"""
    mytool = bpy.context.scene.my_tool
    number_of_objects = 0
    for obj in bpy.data.collections[mytool.my_collection.name].all_objects:
        if not is_child(obj):
            number_of_objects += 1

    if number_of_objects < 1:
        raise ValueError("Collection that is selected is empty. Choose different collection or add objects in this collection")

def setup_gravity():
    scene = bpy.context.scene
    scene.gravity = (0,0,-100)
    scene.use_gravity = True

def prepare_environment(renderer: str):
    scene = bpy.context.scene
    mytool = scene.my_tool
    shadow_catcher = scene.objects["ShadowCatcher"]
    scene.render.engine = renderer
    if renderer == "CYCLES":
        shadow_catcher.hide_render = False
        scene.render.film_transparent = True
        scene.display_settings.display_device = 'sRGB'
        scene.view_settings.view_transform = 'Filmic'
        bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[1].default_value = mytool.environment_strength
        scene.render.filter_size = 1.5
    elif renderer == "BLENDER_EEVEE":
        shadow_catcher.hide_render = True
        scene.render.film_transparent = False
        scene.display_settings.display_device = 'None'
        scene.render.filter_size = 0
        bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[1].default_value = 0

def materialize_objects(material: str):
    """Clear object materials and append material"""
    mytool = bpy.context.scene.my_tool
    index = 0
    for obj in bpy.data.collections[mytool.my_collection.name].all_objects:
        if is_child(obj):
            continue
        obj.data.materials.clear()
        material_name = ""
        if material == "Emission":
            material_name = "Emission " + str(index)
        elif material == "Realistic":
            material_name = obj.name + "_MAT"
        else:
            raise ValueError("ERROR DEFINING MATERIAL")

        obj.data.materials.append(bpy.data.materials[material_name])
        index += 1

def place_objects():
    """Foreach object in collection define object's location"""
    mytool = bpy.context.scene.my_tool
    index = 0
    for obj in bpy.data.collections[mytool.my_collection.name].all_objects:
        if is_child(obj):
            continue
        angle = random.uniform(0, math.radians(360))
        r = random.uniform(0, mytool.max_offset)
        x = r * math.cos(angle)
        y = r * math.sin(angle)
        dimensions = obj.dimensions
        distance = math.sqrt(max(dimensions.x, dimensions.y, dimensions.z))
        z = distance
        obj.location = x, y, z
        index += 1

def rotate_objects():
    """Foreach object in collection define object's rotation"""
    mytool = bpy.context.scene.my_tool
    for obj in bpy.data.collections[mytool.my_collection.name].all_objects:
        if is_child(obj):
            continue
        rng = random.randint(0,1)
        if rng == 0:
            rx = random.randint(0, 359)
            ry = random.randint(0, 359)
            rz = random.randint(0, 359)
            rotation = [rx, ry, rz]
        else:
            f_axis = obj['default_angles'][3]
            rx = obj['default_angles'][0]
            ry = obj['default_angles'][1]
            rz = obj['default_angles'][2]
            rotation = [rx, ry, rz]
            rotation[f_axis] = random.randint(0, 359)

        rx = math.radians(rotation[0])
        ry = math.radians(rotation[1])
        rz = math.radians(rotation[2])
        obj.rotation_euler = (rx, ry, rz)

def simulate():
    mytool = bpy.context.scene.my_tool
    bpy.ops.object.select_all(action='DESELECT')

    for obj in bpy.data.collections[mytool.my_collection.name].objects:
        if not obj.rigid_body:
            continue
    
    bpy.context.scene.frame_end = 1 * bpy.context.scene.render.fps # x secs

    bpy.context.scene.frame_set(1)
    bpy.ops.screen.animation_play()
    for i in range(bpy.context.scene.frame_end):
        bpy.context.scene.frame_set(bpy.context.scene.frame_current + 1)

def render_scene():
    """Position, rotate object and make render"""
    scene = bpy.context.scene
    mytool = scene.my_tool
    
    for image in range(mytool.number_of_images):
        # Set objects location and rotation
        place_objects()
        rotate_objects()
        simulate()
        
        offset = mytool.image_offset + image

        # Render realistic
        prepare_environment("CYCLES")
        materialize_objects("Realistic")
        output_file_pattern_string = 'images/render%d.jpg'
        scene.render.filepath = os.path.join(mytool.output_path, (output_file_pattern_string % offset))
        bpy.ops.render.render(write_still = True)

        # Render black
        prepare_environment("BLENDER_EEVEE")
        materialize_objects("Emission")
        output_file_pattern_string = 'black/render%d.jpg'
        scene.render.filepath = os.path.join(mytool.output_path, (output_file_pattern_string % offset))
        bpy.ops.render.render(write_still = True)

        bpy.ops.screen.animation_cancel(restore_frame=True)
            
    # Set normal color mode
    prepare_environment("CYCLES")
    materialize_objects("Realistic")
    
def setup_background():
    """Make background image on render"""

    # General settings
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.use_nodes = True
    compositor = bpy.context.scene.node_tree

    # Get background image struct
    active_cam = bpy.context.scene.camera.name
    bg_images = bpy.data.objects[active_cam].data.background_images.items()

    # Get background image data, if it exists in struct
    try:
        image = bg_images[0][1].image
        image_scale = bg_images[0][1].scale
    except:
        sys.exit("No Background Found")


    # Create new compositor node, if it not already exists
    node_names = {"bg_image_node":"CompositorNodeImage", "alpha_over_node":"CompositorNodeAlphaOver", "frame_method_node":"CompositorNodeScale", "scale_node":"CompositorNodeScale"}
    current_nodes = compositor.nodes.keys()

    for name,type in node_names.items():
        if name not in current_nodes:
            node = compositor.nodes.new(type=type)
            node.name = name
            

    # Edit compositor nodes  
    bg_image_node = compositor.nodes["bg_image_node"]
    bg_image_node.image = image

    alpha_over_node = compositor.nodes["alpha_over_node"]
    alpha_over_node.location[0] = 600

    frame_method_node = compositor.nodes["frame_method_node"]
    frame_method_node.space = "RENDER_SIZE"
    frame_method_node.location[0] = 200

    scale_node = compositor.nodes["scale_node"]
    scale_node.inputs[1].default_value = image_scale
    scale_node.inputs[2].default_value = image_scale
    scale_node.location[0] = 400


    # Link compositor nodes
    compositor.links.new(compositor.nodes["Render Layers"].outputs[0], alpha_over_node.inputs[2])
    compositor.links.new(bg_image_node.outputs[0], frame_method_node.inputs[0])
    compositor.links.new(frame_method_node.outputs[0], scale_node.inputs[0])
    compositor.links.new(scale_node.outputs[0], alpha_over_node.inputs[1])
    compositor.links.new(alpha_over_node.outputs[0], compositor.nodes["Composite"].inputs[0])

def setup_shadow_catcher():
    """If there is no shadow catcher add one and configure it"""
    scene = bpy.context.scene
    catcher = bpy.context.scene.objects.get("ShadowCatcher")

    if not catcher:
        plane = bpy.ops.mesh.primitive_plane_add(
            size=10, 
            enter_editmode=False, 
            align='WORLD', 
            location=(0, 0, 0), 
            scale=(1, 1, 1))

        bpy.ops.rigidbody.object_add()
        bpy.context.object.rigid_body.type = 'PASSIVE'
            
        # Make planes name ShadowCatcher
        bpy.context.object.name = "ShadowCatcher"
        # Set scene visibility
        bpy.context.object.hide_set(True)
        # Switch to Cycles, turn shadow_catcher on, switch back to Eevee
        scene.render.engine = 'CYCLES'
        bpy.context.object.is_shadow_catcher = True
        scene.render.engine = "BLENDER_EEVEE"

    else:
        # Set scene visibility
        catcher.hide_set(True)
        # Switch to Cycles, turn shadow_catcher on, switch back to Eevee
        scene.render.engine = 'CYCLES'
        catcher.is_shadow_catcher = True
        scene.render.engine = "BLENDER_EEVEE"

def setup_materials():
    """Delete all materials except _MAT materials, create Emmision materials, delete camera and light and create shadow catcher"""
    scene = bpy.context.scene
    mytool = scene.my_tool

    number_of_objects = 0
    for obj in bpy.data.collections[mytool.my_collection.name].all_objects:
        if not is_child(obj):
            number_of_objects += 1
    
    # Remove all materials that are not _MAT
    for material in bpy.data.materials:
        if material.name[-4:] != "_MAT":
            material.user_clear()
            bpy.data.materials.remove(material)
    
    # Create emmision materials
    for i in range(number_of_objects):
        emmision_mat = bpy.data.materials.new(name="Emission "+ str(i))
        emmision_mat.use_nodes = True
        r = (i+1) * (255 / number_of_objects)
        rgb_color = (r/255, 0, 0, 1)
        emmision_mat.node_tree.nodes["Principled BSDF"].inputs["Emission"].default_value = rgb_color
        emmision_mat.node_tree.nodes["Principled BSDF"].inputs["Specular"].default_value = 0
        emmision_mat.node_tree.nodes["Principled BSDF"].inputs["Subsurface Radius"].default_value = (0, 0, 0)
        emmision_mat.node_tree.nodes["Principled BSDF"].inputs["Subsurface IOR"].default_value = 0
        emmision_mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0
        emmision_mat.node_tree.nodes["Principled BSDF"].inputs["Sheen Tint"].default_value = 0
        emmision_mat.node_tree.nodes["Principled BSDF"].inputs["Clearcoat Roughness"].default_value = 0
        emmision_mat.node_tree.nodes["Principled BSDF"].inputs["IOR"].default_value = 0
    
# ------------------------------------------------------------------------
#    Operators
# ------------------------------------------------------------------------

class WM_OT_ExecuteButton(Operator):
    bl_label = "Execute"
    bl_idname = "wm.execute_button"

    # On click
    def execute(self, context):

        verify_collection()
        setup_output_folder()
        setup_gravity()
        setup_materials()
        setup_shadow_catcher()
        setup_background()
        render_scene()
        
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Panel in Object Mode
# ------------------------------------------------------------------------

class OBJECT_PT_CustomPanel(Panel):
    bl_label = "Render Panel"
    bl_idname = "OBJECT_PT_custom_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tools"
    bl_context = "objectmode"

    @classmethod
    def poll(self,context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool
        rd = context.scene.render

        resX = rd.resolution_percentage * rd.resolution_x / 100
        resY = rd.resolution_percentage * rd.resolution_y / 100
        layout.prop(rd, "resolution_percentage", text=f"{resX}x{resY}")
        layout.prop(mytool, "environment_strength")
        layout.prop(mytool, "max_offset")
        layout.prop(mytool, "number_of_images")
        layout.prop(mytool, "my_collection")
        layout.prop(mytool, "output_path")
        layout.prop(mytool, "image_offset")
        layout.operator("wm.execute_button")

# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = (
    MyProperties,
    WM_OT_ExecuteButton,
    OBJECT_PT_CustomPanel
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.my_tool = PointerProperty(type=MyProperties)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.my_tool

if __name__ == "__main__":
    register()
