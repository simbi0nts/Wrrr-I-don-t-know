#!/usr/bin/sudo python

import keyboard
import random
import time
import tkinter as tk

from map import MAPPING
import settings as sett


test_map = [
    ['0' if random.randint(0, 5) and not (x in [1, sett.X_CELLS-1] or y in [1, sett.Y_CELLS-1]) else '1'
     for x in range(sett.X_CELLS)
     ] for y in range(sett.Y_CELLS)
]


class TkEngine(tk.Frame):

    def __init__(self):
        tk.Frame.__init__(self)
        self.master.title("Wrrr, I don't know")
        self.grid()
        frame1 = tk.Frame(self)
        frame1.grid()
        self.canvas = tk.Canvas(frame1, width=sett.VISIBLE_WIDTH, height=sett.VISIBLE_HEIGHT, bg="white")
        self.canvas.grid(columnspan=3)
        self.canvas.focus_set()

        self.camera_borders = 150

        self.light_radius = 150
        self.shadow_gap = 0  # = 4 Kinda experimented feature

        self.glitch_enemy_light_damage = 0.25
        self.glitch_enemy_move_step = 8

        self.smart_enemy_light_damage = 0.5
        self.smart_enemy_move_step = 2

        self.player_break_time = 8
        self.player_move_step = 5

        self.player_start_coords = [
            int(sett.VISIBLE_WIDTH / MAPPING['@']['size']),
            int(sett.VISIBLE_HEIGHT / MAPPING['@']['size'])
        ]
        self.player_cur_coords = [
            self.player_start_coords[0] + int(sett.WIDTH / 2),
            self.player_start_coords[1] + int(sett.HEIGHT / 2)
        ]

        self.sleep_after_move = False
        self.sleep_time = 0.05

        self.last_time = time.time()
        self.timeout = 1
        self.timeout_light_fading = 1

        self.objects = []
        self.player_obj = {}

        self.map_shift = [
            -self.player_cur_coords[0] + int(sett.VISIBLE_WIDTH / 2),
            -self.player_cur_coords[1] + int(sett.VISIBLE_HEIGHT / 2)
        ]

    def new_game(self):
        self.render_canvas_map(test_map)
        self.create_player_obj()
        self.put_enemies_on_map('re', _count=10)
        self.put_enemies_on_map('se', _count=15)
        self.update_lighting(force=True)
        self.move_canvas_on_init()
        self.movement_handler()

    def move_canvas_on_init(self):
        self.canvas.move(tk.ALL, -self.player_cur_coords[0] + int(sett.VISIBLE_WIDTH / 2),
                         -self.player_cur_coords[1] + int(sett.VISIBLE_HEIGHT / 2))

    def render_canvas_map(self, _map):
        for y in range(len(_map)):
            for x in range(len(_map[y])):
                _mapping = MAPPING[_map[y][x]]
                tag = _mapping['tag']
                color = _mapping['color']
                outline_color = _mapping.get('outline_color') or color
                cell_size = _mapping['size']
                width = _mapping.get('outline_width') or 0

                self.objects.append({
                    'tag': tag,
                    'x': (x * cell_size + (cell_size / 2)),
                    'y': (y * cell_size + (cell_size / 2)),
                    'size': cell_size,
                    'fill': color,
                    'outline': outline_color,
                    'width': width
                })

    def create_player_obj(self):
        player_coords = self.player_cur_coords
        _mapping = MAPPING['@']
        tag = _mapping['tag']
        color = _mapping['color']
        size = _mapping['size']
        outline_color = _mapping.get('outline_color') or '#111'

        self.player_obj = {
            'x': player_coords[0] + size / 2,
            'y': player_coords[1] + size / 2,
            'size': size,
            'outline': outline_color,
            'fill': color,
            'tag': tag,
        }

    def put_enemies_on_map(self, enemy_type_code, _count=10):
        _mapping = MAPPING[enemy_type_code]
        tag = _mapping['tag']
        color = _mapping['color']
        size = _mapping['size']

        _border_delay = 35

        for x in range(_count):
            while True:
                repeat = False
                _x, _y = [random.randint(_border_delay, sett.WIDTH - _border_delay),
                          random.randint(_border_delay, sett.HEIGHT - _border_delay)]

                for obj in self.objects:
                    if obj['x'] - obj['size'] / 4 <= _x <= obj['x'] + obj['size'] / 4 and \
                       obj['y'] - obj['size'] / 4 <= _y <= obj['y'] + obj['size'] / 4 and \
                       obj['tag'] in ['wall', 'smart_enemy', 'glitch_enemy']:
                        repeat = True
                        break

                if not repeat:
                    self.objects.append({
                        'x': _x + size / 2,
                        'y': _y + size / 2,
                        'tag': tag,
                        'size': size,
                        'fill': color,
                        'outline': '#f66'
                    })
                    break

    def update(self):
        self.render()
        self.glitch_enemies_move()
        self.smart_enemies_move()
        self.update_lighting()
        self.apply_shadows()
        self.master.update_idletasks()
        self.master.update()

    def render(self):
        self.canvas.delete(tk.ALL)

        _mapping = MAPPING['@']
        size = _mapping['size']

        pl_c = self.player_cur_coords
        pl_c_x = pl_c[0] + size / 2
        pl_c_y = pl_c[1] + size / 2
        lrq = (self.light_radius + 10) ** 2

        xms = self.map_shift[0]
        yms = self.map_shift[1]

        for obj in self.objects:
            if (obj['x'] - pl_c_x) ** 2 + (obj['y'] - pl_c_y) ** 2 < lrq:
                self.canvas.create_rectangle(obj['x'] - obj['size'] / 2 + xms, obj['y'] - obj['size'] / 2 + yms,
                                             obj['x'] + obj['size'] / 2 + xms, obj['y'] + obj['size'] / 2 + yms,
                                             outline=obj['outline'], fill=obj['fill'], tag=obj['tag'],
                                             width=obj.get('width', 0))
        self.create_player_obj()
        sp = self.player_obj
        self.canvas.create_rectangle(sp['x'] - sp['size'] / 2 + xms, sp['y'] - sp['size'] / 2 + yms,
                                     sp['x'] + sp['size'] / 2 + xms, sp['y'] + sp['size'] / 2 + yms,
                                     outline=sp['outline'], fill=sp['fill'], tag=sp['tag'])

    def glitch_enemies_move(self):
        moves = {
            'UP': [0, -1],
            'DOWN': [0, 1],
            'LEFT': [-1, 0],
            'RIGHT': [1, 0]
        }

        for obj in self.objects:
            if obj['tag'] in ['glitch_enemy'] and not random.randint(0, 3):
                if random.randint(0, 1):
                    move_dir, diff = random.choice(list(moves.items()))
                    self.move(obj, move_dir, diff[0], diff[1], self.glitch_enemy_move_step, 0)
                else:
                    for move_dir in random.choice(sett.DIAGONAL_DIRECTIONS):
                        self.move(obj, move_dir, moves[move_dir][0], moves[move_dir][1],
                                  self.glitch_enemy_move_step * 0.8, 0)

    def smart_enemies_move(self):
        for obj in self.objects:
            if obj['tag'] in ['smart_enemy']:
                center_x = obj['x']
                center_y = obj['y']

                lr = self.light_radius
                sp = self.player_obj
                is_player_nearby = center_x - lr < sp['x'] < center_x + lr and center_y - lr < sp['y'] < center_y + lr

                if is_player_nearby:
                    n_center_x = sp['x']
                    n_center_y = sp['y']
                    diff_x = -(n_center_x - center_x < 0) or int(n_center_x - center_x > 0)
                    diff_y = -(n_center_y - center_y < 0) or int(n_center_y - center_y > 0)
                    self.move(obj, 'towards_player', 0, diff_y, self.smart_enemy_move_step, 0)
                    self.move(obj, 'towards_player', diff_x, 0, self.smart_enemy_move_step, 0)
                    break

    def is_objects_collide(self, obj, list_of_colliding_objs):
        xs = [obj['x'] - obj['size'] / 2, obj['x'] + obj['size'] / 2]
        ys = [obj['y'] - obj['size'] / 2, obj['y'] + obj['size'] / 2]

        items = [
            itm for itm in self.objects if xs[0] < itm['x'] < xs[1] and ys[0] < itm['y'] < ys[1]
        ]

        for item in items:
            obj_name = item['tag']
            if obj_name in list_of_colliding_objs:
                return True, obj_name
        return False, None

    def update_lighting(self, force=False):
        is_hurt, obj = self.is_objects_collide(self.player_obj, ['glitch_enemy', 'smart_enemy'])
        if is_hurt:
            if obj == 'glitch_enemy':
                self.light_radius -= self.glitch_enemy_light_damage
            if obj == 'smart_enemy':
                self.light_radius -= self.smart_enemy_light_damage
            force = True

        cur_time = time.time()
        if cur_time - self.last_time > self.timeout or force:
            self.last_time = cur_time
            self.light_radius -= self.timeout_light_fading
        self.create_light('player', 'main_light')

    def create_light(self, obj, tag):
        self.canvas.delete(tag)
        shadow_color = '#111'

        lr = sett.WIDTH - self.light_radius
        w = sett.WIDTH * 2
        _w = w - lr

        coords = self.canvas.coords(obj)

        center_x = sum(coords[::2]) / 2
        center_y = sum(coords[1::2]) / 2

        self.canvas.create_arc(center_x - _w, center_y - _w, center_x + _w, center_y + _w,
                               start=0, extent=180, style=tk.ARC, outline=shadow_color, width=w, tag=tag)
        self.canvas.create_arc(center_x - _w, center_y - _w, center_x + _w, center_y + _w,
                               start=180, extent=180, style=tk.ARC, outline=shadow_color, width=w, tag=tag)

    def apply_shadows(self):
        self.canvas.delete('shadow')
        shadow_color = '#111'

        lr = self.light_radius
        coords = self.canvas.coords('player')
        center_x = sum(coords[::2]) / 2
        center_y = sum(coords[1::2]) / 2

        sg = self.shadow_gap

        xms = self.map_shift[0]
        yms = self.map_shift[1]

        items = [
            itm for itm in self.objects if
            center_x - lr < itm['x'] + xms < center_x + lr and
            center_y - lr < itm['y'] + yms < center_y + lr
        ]

        for item in items:
            collide_obj = item['tag']
            points = []
            if collide_obj in ['wall']:
                ''' That's where the fun begins 
                    Notice, that order of points is matter
                '''
                x1, y1, x2, y2 = [
                    item['x'] - item['size'] / 2 + xms, item['y'] - item['size'] / 2 + yms,
                    item['x'] + item['size'] / 2 + xms, item['y'] + item['size'] / 2 + yms
                ]

                # upper-left segment
                if x2 < center_x and y2 < center_y:
                    points = [x1, y2, x2 - sg, y2 - sg, x2, y1]

                # upper-right segment
                if x1 > center_x and y2 < center_y:
                    points = [x1, y1, x1 + sg, y2 - sg, x2, y2]

                # lower-left segment
                if x2 < center_x and y2 > center_y:
                    points = [x2, y2, x2 - sg, y1 + sg, x1, y1]

                # lower-right segment
                if x1 > center_x and y2 > center_y:
                    points = [x2, y1, x1 + sg, y1 + sg, x1, y2]

                # above
                if x1 <= center_x <= x2 and y2 <= center_y:
                    points = [x1, y2 - sg, x2, y2 - sg]

                # under
                if x1 <= center_x <= x2 and y1 >= center_y:
                    points = [x2, y1 + sg, x1, y1 + sg]

                # left
                if x2 <= center_x and y1 <= center_y <= y2:
                    points = [x2 - sg, y2, x2 - sg, y1]

                # right
                if x2 >= center_x and y1 <= center_y <= y2:
                    points = [x1 + sg, y1, x1 + sg, y2]

                center = None
                for coord in points[-2:] + points[:2]:
                    center = center_x if center != center_x else center_y
                    points.append(center - lr * (center - coord))

                self.canvas.create_polygon(points, fill=shadow_color, tag='shadow')

    def get_next_step_collide_objects(self, obj, x_diff, y_diff):
        """ Looking for next-step collides and distance between them and object """

        def is_near_and_overlaping(xs, ys, itm):
            center_x = sum(xs) / 2
            center_y = sum(ys) / 2
            m_diff = max(abs(x_diff), abs(y_diff)) ** 2
            if abs(center_x - itm['x']) > m_diff or abs(center_y - itm['y']) > m_diff:
                return False

            for x in xs:
                for y in ys:
                    if itm['x'] - itm['size'] / 2 <= x + x_diff <= itm['x'] + itm['size'] / 2 and \
                       itm['y'] - itm['size'] / 2 <= y + y_diff <= itm['y'] + itm['size'] / 2:
                        return True
            return False

        collides = dict()
        xs = [obj['x'] - obj['size'] / 2, obj['x'] + obj['size'] / 2]
        ys = [obj['y'] - obj['size'] / 2, obj['y'] + obj['size'] / 2]

        items = [itm for itm in self.objects if is_near_and_overlaping(xs, ys, itm)]

        for item in items:
            collide_obj = item['tag']
            coords = [
                item['x'] - item['size'] / 2, item['y'] - item['size'] / 2,
                item['x'] + item['size'] / 2, item['y'] + item['size'] / 2
            ]

            for _x in xs:
                for _y in ys:
                    next_x, next_y = _x + x_diff, _y + y_diff

                    if next_x < 0 or next_y < 0:
                        collides['map_border'] = [
                            -min(xs) if x_diff else 0, -min(ys) if y_diff else 0
                        ]

                    elif next_x > sett.WIDTH or next_y > sett.HEIGHT:
                        collides['map_border'] = [
                            sett.VISIBLE_WIDTH - max(xs) if x_diff else 0,
                            sett.VISIBLE_HEIGHT - max(ys) if y_diff else 0
                        ]

                    else:
                        if coords[0] < next_x < coords[2] and coords[1] < next_y < coords[3]:
                            if x_diff < 0:
                                collides[collide_obj] = [coords[2] - _x, 0]
                            if x_diff > 0:
                                collides[collide_obj] = [coords[0] - _x - 1, 0]
                            if y_diff < 0:
                                collides[collide_obj] = [0, coords[3] - _y]
                            if y_diff > 0:
                                collides[collide_obj] = [0, coords[1] - _y - 1]

        return collides

    @staticmethod
    def is_enemy(collide_objects):
        return 'smart_enemy' in collide_objects or 'glitch_enemy' in collide_objects

    @staticmethod
    def is_map_border(collide_objects):
        return 'map_border' in collide_objects

    @staticmethod
    def is_wall(collide_objects):
        return 'wall' in collide_objects

    def move(self, obj, action, x_diff, y_diff, move_step=sett.CELL_SIZE, break_time=50, lightning_obj=None):
        collide_objects = self.get_next_step_collide_objects(obj, move_step * x_diff, move_step * y_diff)

        is_enemy_ahead = self.is_enemy(collide_objects)
        is_wall_ahead = self.is_wall(collide_objects)
        is_border_ahead = self.is_map_border(collide_objects)

        if not is_wall_ahead and not is_border_ahead and not is_enemy_ahead:
            coords = [
                move_step * x_diff,
                move_step * y_diff
            ]

        elif is_wall_ahead:
            coords = collide_objects.get('wall', [0, 0])

        elif is_border_ahead:
            coords = collide_objects.get('map_border', [0, 0])

        elif obj['tag'] == 'player' and is_enemy_ahead:
            coords = [
                move_step * x_diff,
                move_step * y_diff
            ]

        elif obj['tag'] in ['smart_enemy', 'glitch_enemy'] and is_enemy_ahead:
            coords = [0, 0]

        else:
            coords = [0, 0]

        if obj['tag'] == 'player':
            self.player_cur_coords = [
                self.player_cur_coords[0] + coords[0],
                self.player_cur_coords[1] + coords[1]
            ]
            _coords = self.canvas.coords('player')

            if self.camera_borders < self.player_cur_coords[0] < sett.WIDTH - self.camera_borders and x_diff:
                center_x = sum(_coords[::2]) / 2
                ms = move_step * x_diff
                if not (self.camera_borders < center_x + ms < sett.VISIBLE_WIDTH - self.camera_borders):
                    self.map_shift[0] -= coords[0]
                    self.map_shift[1] -= coords[1]

            if self.camera_borders < self.player_cur_coords[1] < sett.HEIGHT - self.camera_borders and y_diff:
                center_y = sum(_coords[1::2]) / 2
                ms = move_step * y_diff
                if not (self.camera_borders < center_y + ms < sett.VISIBLE_HEIGHT - self.camera_borders):
                    self.map_shift[0] -= coords[0]
                    self.map_shift[1] -= coords[1]
                    # self.canvas.move(tk.ALL, -coords[0]*5, -coords[1]*5)

        obj['x'] += coords[0]
        obj['y'] += coords[1]
        if lightning_obj:
            self.canvas.move(lightning_obj, coords[0], coords[1])
        self.canvas.after(break_time)

    def is_diagonal_move(self):
        for dir1, dir2 in sett.DIAGONAL_DIRECTIONS:
            if self.keyboard_is_pressed_from_list(sett.MOVEMENT_KEYS[dir1]) and \
                    self.keyboard_is_pressed_from_list(sett.MOVEMENT_KEYS[dir2]):
                return True
        return False

    @staticmethod
    def keyboard_is_pressed_from_list(arr):
        return bool(sum([keyboard.is_pressed(value) for value in arr]))

    def movement_handler(self):
        while True:
            self.update()
            break_time = self.player_break_time
            try:
                if self.is_diagonal_move():
                    break_time = int(break_time * 0.8)

                if self.keyboard_is_pressed_from_list(sett.MOVEMENT_KEYS['UP']):
                    self.move(self.player_obj, 'UP', 0, -1, self.player_move_step, break_time, 'main_light')

                if self.keyboard_is_pressed_from_list(sett.MOVEMENT_KEYS['DOWN']):
                    self.move(self.player_obj, 'DOWN', 0, 1, self.player_move_step, break_time, 'main_light')

                if self.keyboard_is_pressed_from_list(sett.MOVEMENT_KEYS['LEFT']):
                    self.move(self.player_obj, 'LEFT', -1, 0, self.player_move_step, break_time, 'main_light')

                if self.keyboard_is_pressed_from_list(sett.MOVEMENT_KEYS['RIGHT']):
                    self.move(self.player_obj, 'RIGHT', 1, 0, self.player_move_step, break_time, 'main_light')

            except Exception as e:
                break


def main():
    Game = TkEngine()
    Game.new_game()
if __name__ == '__main__':
    main()
