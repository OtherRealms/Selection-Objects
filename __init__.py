# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name" : "SelectionObjects",
    "author" : "Pablo Tochez A.",
    "description" : "Use a selection mesh/s to select verts on active object",
    "blender" : (2, 80, 0),
    "version" : (0, 0, 2),
    "location" : "Edit Mode->select->selection objects",
    "warning" : "",
    "category" : "Mesh"
}


import bpy
import bmesh
from bpy.props import*
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np

positions = []
obj_selection  = []

class MESH_OT_selection_object(bpy.types.Operator):

    bl_idname = "mesh.selection_object"
    bl_label = "Use selection object"
    bl_description = "Project selected vertices or use mesh volume from other objects. Selected to Active. Must be in Vertex selection mode."
    bl_options = {'REGISTER','UNDO'}

    accuracy: IntProperty(default = 2,min = 0,max = 4,description= "Lower values are more accurate")
    mode: EnumProperty(items = (
        ('VERTEX','Vertex','Select using vertex proximity'),
        ('VOLUME','Volume','Select vertices within mesh volume'),
        ))

    @classmethod
    def poll(self,context):
        return context.mode == 'EDIT_MESH' and context.tool_settings.mesh_select_mode[0] 


    def execute(self,context):
        
        # Get the active mesh
        obj_active = context.edit_object
        obj_active_data = obj_active.data
        obj_selection.clear()
        print("----------")
        #selecetion objects

        if len(context.selected_objects) > 0:
            for obj in context.selected_objects:
                if obj != context.active_object:
                    obj_selection.append(obj)
        else:
            self.report({'ERROR'},"No selection objects!")
            return{'CANCELLED'}
            
        bm = bmesh.from_edit_mesh(obj_active_data)
        bm.faces.active = None
        bm.select_flush(True)
        if hasattr(bm.verts, "ensure_lookup_table"): 
            bm.verts.ensure_lookup_table()

        
        if self.mode == 'VERTEX':
            self.vert_proximity(context,bm,obj_active)
        elif self.mode == 'VOLUME':
            self.volume(context,bm,obj_active)


        return {'FINISHED'}

    def vert_proximity(self,context,bm,obj_active):
        accuracy = str(self.accuracy)
        positions.clear()

        for obj in obj_selection:
            for vert in obj.data.vertices:
                vector = []
                co = obj.matrix_world @ vert.co
                
                for pos in co:
                    vector.append(format(pos,'.'+ accuracy +'f'))
                positions.append(vector)

        for vert in obj_active.data.vertices:
            vector = []
            co = obj_active.matrix_world @ vert.co
            
            for pos in co:
                vector.append(format(pos,'.'+ accuracy +'f'))

            if vector in positions:
                bm.verts[vert.index].select_set(True)
                #print('MATCH',vector,vert.index)



        bmesh.update_edit_mesh(obj_active.data)

    def volume(self,context,bm,obj_active):

        obj_active_data = obj_active.data

        dg = bpy.context.evaluated_depsgraph_get()

        if hasattr(bm.verts, "ensure_lookup_table"): 
            bm.verts.ensure_lookup_table()

        bvh_list = []

        
        for mesh_obj in obj_selection:
            #bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            bm_sel = bmesh.new()

            #bm = bmesh.from_edit_mesh(mesh_obj.data)
            bm_sel.from_object(mesh_obj , dg)
            #print(bm)

            bmesh.ops.transform(bm_sel, matrix= mesh_obj.matrix_world, verts= bm_sel.verts)

            bvh_list.append((BVHTree.FromBMesh(bm_sel, epsilon=self.accuracy * 0.001),mesh_obj.dimensions))


        for vert in obj_active_data.vertices:
            point_local = obj_active.matrix_world @ vert.co
            if self.is_inside(context,point_local,bvh_list):
                bm.verts[vert.index].select_set(True)
                #print('MATCH',vert.index)
           
        bmesh.update_edit_mesh(obj_active_data)
        

    def is_inside(self,context,point_local,bvh_list):
        for bvh,dimensions in bvh_list:
            point_loc, normal, index, distance = bvh.find_nearest(point_local)
            vec = point_loc - Vector(point_local)
            max_dist = max(dimensions)
            if distance < max_dist:
                dot_prod = vec.dot(normal)

                if dot_prod > 0.0:
                    return True

        return False



class add_to_menu(object):
    def draw(self,context):
        self.layout.operator("mesh.selection_object")


def register():
    bpy.utils.register_class(MESH_OT_selection_object)

    bpy.types.VIEW3D_MT_select_edit_mesh.append(add_to_menu.draw)

def unregister():
    bpy.utils.unregister_class(MESH_OT_selection_object)
    bpy.types.VIEW3D_MT_select_edit_mesh.remove(add_to_menu.draw)

