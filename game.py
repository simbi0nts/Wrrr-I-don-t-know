#!/usr/bin/sudo python

import keyboard
import random
import tkinter as tk

from map import MAP as MAPPING
import settings as sett


# TODO: cleanup
WIDTH = 500
HEIGHT = 500

CELL_SIZE = MAPPING['1']['size']
HALF_CELL_SIZE = CELL_SIZE / 2

X_CELLS = int(WIDTH / CELL_SIZE)
Y_CELLS = int(HEIGHT / CELL_SIZE)
test_map = [['0' if random.randint(0, 10) else '1' for x in range(X_CELLS)] for y in range(Y_CELLS)]

DIAGONAL_DIRECTIONS = (('UP', 'RIGHT'), ('UP', 'LEFT'), ('DOWN', 'RIGHT'), ('DOWN', 'LEFT'))


class TkEngine(tk.Frame):

    def __init__(self):
        tk.Frame.__init__(self)
        self.master.title("Wrrr, I don't know")
        self.grid()
        frame1 = tk.Frame(self)
        frame1.grid()
        self.canvas = tk.Canvas(frame1, width=WIDTH, height=HEIGHT, bg="white")
        self.canvas.grid(columnspan=3)
        self.canvas.focus_set()

        self.light_radius = 150
        self.shadow_gap = 0  # = 4 Kinda experimented feature
        self.player_move_step = 5
        self.player_break_time = 20
        self.sleep_after_move = False
        self.sleep_time = 0.05

    def new_game(self):
        self.render_canvas_map()
        self.put_player_on_map()
        self.create_light('player', 'main_light')
        self.movement_handler()

    def render_canvas_map(self):
        for y in range(len(test_map)):
            for x in range(len(test_map[y])):
                _mapping = MAPPING[test_map[y][x]]
                tag = _mapping['tag']
                color = _mapping['color']
                outline_color = _mapping.get('outline_color') or color
                cell_size = _mapping['size']
                width = _mapping.get('outline_width') or 0
                self.canvas.create_rectangle(x*cell_size, y*cell_size,
                                             (x+1)*cell_size, (y+1)*cell_size,
                                             outline=outline_color, width=width, fill=color, tag=tag)

    def put_player_on_map(self):
        player_coords = (15, 15)  # test
        _mapping = MAPPING['@']
        tag = _mapping['tag']
        color = _mapping['color']
        size = _mapping['size']
        self.canvas.create_rectangle(player_coords[0]*size, player_coords[1]*size,
                                     (player_coords[0]+1)*size-1, (player_coords[1]+1)*size-1,
                                     outline='#111', fill=color, tag=tag)

    def update(self):
        self.apply_shadows()
        self.master.update_idletasks()
        self.master.update()

    def create_light(self, obj, tag):
        lr = WIDTH - self.light_radius
        w = WIDTH*2
        _w = w - lr
        coords = self.canvas.coords(obj)
        center_x = sum(coords[::2])/2
        center_y = sum(coords[1::2])/2
        self.canvas.create_arc(center_x-_w, center_y-_w, center_x+_w, center_x+_w,
                               start=0, extent=359, style=tk.ARC, outline="#111", width=w, tag=tag)
        self.canvas.create_arc(center_x-_w, center_y-_w, center_x+_w, center_x+_w,
                               start=359, extent=1, style=tk.ARC, outline="#111", width=w, tag=tag)

    def apply_shadows(self):
        self.canvas.delete('shadow')

        lr = self.light_radius
        coords = self.canvas.coords('player')
        center_x = sum(coords[::2])/2
        center_y = sum(coords[1::2])/2

        sg = self.shadow_gap

        items = self.canvas.find_overlapping(center_x-lr, center_y-lr, center_x+lr, center_y+lr)
        for item in items:
            collide_obj = self.canvas.gettags(item)[0]
            points = []
            if collide_obj in ['wall']:
                ''' That's where the fun begins 
                    Notice, that order of points is matter
                '''
                x1, y1, x2, y2 = self.canvas.coords(item)

                # upper-left segment
                if x2 < center_x and y2 < center_y:
                    points = [x1, y2, x2-sg, y2-sg, x2, y1]

                # upper-right segment
                if x1 > center_x and y2 < center_y:
                    points = [x1, y1, x1+sg, y2-sg, x2, y2]

                # lower-left segment
                if x2 < center_x and y2 > center_y:
                    points = [x2, y2, x2-sg, y1+sg, x1, y1]

                # lower-right segment
                if x1 > center_x and y2 > center_y:
                    points = [x2, y1, x1+sg, y1+sg, x1, y2]


                # above
                if x1 <= center_x <= x2 and y2 <= center_y:
                    points = [x1, y2-sg, x2, y2-sg]

                # under
                if x1 <= center_x <= x2 and y1 >= center_y:
                    points = [x2, y1+sg, x1, y1+sg]

                # left
                if x2 <= center_x and y1 <= center_y <= y2:
                    points = [x2-sg, y2, x2-sg, y1]

                # right
                if x2 >= center_x and y1 <= center_y <= y2:
                    points = [x1+sg, y1, x1+sg, y2]

                center = None
                for coord in points[-2:] + points[:2]:
                    center = center_x if center != center_x else center_y
                    points.append(center - lr * (center - coord))

                self.canvas.create_polygon(points, fill='#111', tag='shadow')

    def get_next_step_collide_objects(self, obj, x_diff, y_diff):
        """ Looking for next-step collides and distance between them and object """

        collides = dict()
        xs = self.canvas.coords(obj)[::2]
        ys = self.canvas.coords(obj)[1::2]

        items = self.canvas.find_overlapping(xs[0]+x_diff, ys[0]+y_diff, xs[1]+x_diff, ys[1]+y_diff)

        for item in items:
            collide_obj = self.canvas.gettags(item)[0]
            coords = self.canvas.coords(item)

            for _x in xs:
                for _y in ys:
                    next_x, next_y = _x + x_diff, _y + y_diff

                    if next_x < 0 or next_y < 0:
                        collides['map_border'] = [-min(xs) if x_diff else 0, -min(ys) if y_diff else 0]
                    elif next_x > WIDTH or next_y > HEIGHT:
                        collides['map_border'] = [WIDTH-max(xs) if x_diff else 0, HEIGHT-max(ys) if y_diff else 0]
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
    def is_map_border(collide_objects):
        return 'map_border' in collide_objects

    @staticmethod
    def is_wall(collide_objects):
        return 'wall' in collide_objects

    def move(self, obj, action, x_diff, y_diff, move_step=CELL_SIZE, break_time=50, lightning_obj=None):
        """ The movement logic is only accepted for small steps movement
            (less than wall size). Not critical. But unacceptable.
            TODO:
            1) is_step_too_big_check when step > wall size
            2) small_steps_collide_check logic
            Better to do that ASAP, because it's an architecture issue.
            Also, action field is deprecated, legacy and I don't know, why it's still here
        """

        collide_objects = self.get_next_step_collide_objects(obj, move_step * x_diff, move_step * y_diff)
        is_wall_ahead = self.is_wall(collide_objects)
        is_border_ahead = self.is_map_border(collide_objects)

        if not is_wall_ahead and not is_border_ahead:
            coords = [move_step*x_diff, move_step*y_diff]
        elif is_wall_ahead:
            coords = collide_objects.get('wall', [0, 0])
        elif is_border_ahead:
            coords = collide_objects.get('map_border', [0, 0])
        else:
            coords = [0, 0]

        self.canvas.move(obj, coords[0], coords[1])
        if lightning_obj:
            self.canvas.move(lightning_obj, coords[0], coords[1])
        self.canvas.after(break_time)

    def is_diagonal_move(self):
        for dir1, dir2 in DIAGONAL_DIRECTIONS:
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
                    self.move('player', 'up', 0, -1, self.player_move_step, break_time, 'main_light')
                if self.keyboard_is_pressed_from_list(sett.MOVEMENT_KEYS['DOWN']):
                    self.move('player', 'down', 0, 1, self.player_move_step, break_time, 'main_light')
                if self.keyboard_is_pressed_from_list(sett.MOVEMENT_KEYS['LEFT']):
                    self.move('player', 'left', -1, 0, self.player_move_step, break_time, 'main_light')
                if self.keyboard_is_pressed_from_list(sett.MOVEMENT_KEYS['RIGHT']):
                    self.move('player', 'right', 1, 0, self.player_move_step, break_time, 'main_light')
            except Exception as e:
                break


def main():
    Game = TkEngine()
    Game.new_game()
if __name__ == '__main__':
    main()
