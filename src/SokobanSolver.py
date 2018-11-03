from lib.satSolver import SatSolver
from lib.theoryWriter import TheoryWriter
import lib.text2dimacs

class SokobanSolver(object):

    def __init__(self, map_name):
        self.map_data = {}
        self.load_map(map_name)
        self.coords = self.generate_coords()

    def solve(self):
        N = 1
        solver = SatSolver()
        ok = False
        iteration = 1
        while not ok and iteration <= N:
            theory = TheoryWriter('sokoban-in.txt')
            self.encodeInitState(theory)
            theory.writeComment('RULES')
            for step in range(1, iteration + 1):
                self.encode_player_pos(theory, step)
                self.encode_box_pos(theory, step)
                self.encode_player_box_pos(theory, step)
                
                theory.writeComment('Na jednom policku moze byt bud hrac alebo nic alebo nejaky z boxov')
                theory.writeComment('empty(XY, state) or player(XY, state) or at(box_id, XY, state)')
                for box_id in range(len(self.map_data['boxes'])):
                    for XY in self.coords:
                        theory.writeClause([self.empty(XY, step), self.player(XY, step), self.at(box_id+1, XY, step)])

                theory.writeComment('ak je box v cieli tak je na pozicii ktora je oznacena ako target')
                theory.writeComment('in_target(box,s) -> (at(box,XY,s) and target(XY))')
                for box_id in range(len(self.map_data['boxes'])):
                    for XY in self.coords:
                        theory.writeClause([self.neg(self.in_target(box_id+1, step)), self.at(box_id+1, XY, step)])
                        theory.writeClause([self.neg(self.in_target(box_id+1, step)), self.target(XY)])
                
                self.encode_action_move(theory, step)
                self.encode_action_push(theory, step)
                self.encode_action_push_t(theory, step)
                self.encode_actions(theory, step)
            self.encodeGoal(theory, iteration)
            theory.close()
            print('ITERATION:', iteration)
            print('theory writed')
            print('translating to DIMACS ...')
            lib.text2dimacs.translate('sokoban-in.txt', 'sokoban-in-dimacs.txt')
            print('theory translated to dimacs')
            print('solving ...')
            ok, sol = solver.solve('sokoban-in-dimacs.txt','sokoban-out.txt')
            print('theory solved')
            print(ok)
            iteration += 1

    def encode_box_pos(self, theory, step):
        theory.writeComment('Ak je box na nejakej pozicii, nemoze byt zaroven na druhej pozicii')
        for box_id in range(len(self.map_data['boxes'])):
            for c1 in range(len(self.coords)):
                for c2 in range(c1+1, len(self.coords)):
                    theory.writeClause([
                        self.neg(self.at(box_id+1, self.coords[c1], step)),
                        self.neg(self.at(box_id+1, self.coords[c2], step))
                    ])

    def encode_player_pos(self, theory, step):
        theory.writeComment('Ak je hrac na nejakej pozicii, nemoze byt zaroven na druhej pozicii')
        for c1 in range(len(self.coords)):
            for c2 in range(c1 + 1, len(self.coords)):
                theory.writeClause([self.neg(self.player(self.coords[c1], step)), self.neg(self.player(self.coords[c2], step))])

    def encode_player_box_pos(self, theory, step):
        theory.writeComment('na jednej pozicii moze byt bud player alebo nejaky box')
        theory.writeComment('-(player(XY, s) and at(box_id, XY, s))')
        for box_id in range(len(self.map_data['boxes'])):
            for x in range(self.map_data['map_size'][0]):
                for y in range(self.map_data['map_size'][1]):
                    theory.writeClause([
                        '-player({}_{},{})'.format(x,y,step),
                        '-at(box{},{}_{},{})'.format(box_id+1,x,y,step)
                    ])

    def encode_action_move(self, theory, step):
        theory.writeComment('Action move(fromXY, toXY, step)')
        for fromXY in self.coords:
            for toXY in self.coords:
                if self.is_adjacent(fromXY, toXY):
                    # P+
                    theory.writeClause([self.neg(self.move(fromXY, toXY, step)), self.player(fromXY, step-1)])
                    theory.writeClause([self.neg(self.move(fromXY, toXY, step)), self.empty(toXY, step-1)])
                    # E+
                    theory.writeClause([self.neg(self.move(fromXY, toXY, step)), self.player(toXY, step)])
                    theory.writeClause([self.neg(self.move(fromXY, toXY, step)), self.empty(fromXY, step)])
                    # E-
                    theory.writeClause([self.neg(self.move(fromXY, toXY, step)), self.neg(self.empty(toXY, step))])
                    theory.writeClause([self.neg(self.move(fromXY, toXY, step)), self.neg(self.player(fromXY, step))])

    def encode_action_push(self, theory, step):
        theory.writeComment('Action push(box, playerXY, fromXY, toXY, step)')
        for box_id in range(len(self.map_data['boxes'])):
            for playerXY in self.coords:
                for fromXY in self.coords:
                    if self.is_adjacent(playerXY, fromXY):
                        for toXY in self.coords:
                            if self.is_inline(playerXY, fromXY, toXY):
                                theory.writeClause([
                                    self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                    self.empty(toXY, step-1)
                                ])
                                theory.writeClause([
                                    self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                    self.player(playerXY, step-1)
                                ])
                                theory.writeClause([
                                    self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                    self.at(box_id+1, fromXY, step-1)
                                ])
                                theory.writeClause([
                                    self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                    self.neg(self.target(toXY))
                                ])
                                theory.writeClause([
                                    self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                    self.player(fromXY, step)
                                ])
                                theory.writeClause([
                                    self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                    self.at(box_id+1, toXY, step)
                                ])
                                theory.writeClause([
                                    self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                    self.empty(playerXY, step)
                                ])
                                theory.writeClause([
                                    self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                    self.neg(self.empty(toXY, step))
                                ])
                                theory.writeClause([
                                    self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                    self.neg(self.player(playerXY, step))
                                ])
                                theory.writeClause([
                                    self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                    self.neg(self.at(box_id+1, fromXY, step))
                                ])
                                theory.writeClause([
                                    self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                    self.neg(self.in_target(box_id+1, step))
                                ])

    def encode_action_push_t(self, theory, step):
        theory.writeComment('action push_t(box, playerXY, fromXY, toXY, step) rules')
        for box_id in range(len(self.map_data['boxes'])):
            for player_x in range(self.map_data['map_size'][0]):
                for player_y in range(self.map_data['map_size'][1]):
                    for from_x in range(self.map_data['map_size'][0]):
                        for from_y in range(self.map_data['map_size'][1]):
                            if self.is_adjacent((player_x,player_y), (from_x, from_y)):
                                for to_x in range(self.map_data['map_size'][0]):
                                    for to_y in range(self.map_data['map_size'][1]):
                                        if self.is_inline((player_x,player_y), (from_x,from_y), (to_x,to_y)):
                                            # p+
                                            theory.writeClause([
                                                '-push_t(box{},{}_{},{}_{},{}_{},{})'.format(box_id+1,player_x,player_y,from_x,from_y,to_x,to_y,step),
                                                'empty({}_{},{})'.format(to_x,to_y,step-1)
                                            ])
                                            theory.writeClause([
                                                '-push_t(box{},{}_{},{}_{},{}_{},{})'.format(box_id+1,player_x,player_y,from_x,from_y,to_x,to_y,step),
                                                'player({}_{},{})'.format(player_x,player_y,step-1)
                                            ])
                                            theory.writeClause([
                                                '-push_t(box{},{}_{},{}_{},{}_{},{})'.format(box_id+1,player_x,player_y,from_x,from_y,to_x,to_y,step),
                                                'at(box{},{}_{},{})'.format(box_id+1,from_x,from_y,step-1)
                                            ])
                                            theory.writeClause([
                                                '-push_t(box{},{}_{},{}_{},{}_{},{})'.format(box_id+1,player_x,player_y,from_x,from_y,to_x,to_y,step),
                                                'target({}_{})'.format(to_x,to_y)
                                            ])
                                            # e+
                                            theory.writeClause([
                                                '-push_t(box{},{}_{},{}_{},{}_{},{})'.format(box_id+1,player_x,player_y,from_x,from_y,to_x,to_y,step),
                                                'player({}_{},{})'.format(from_x,from_y,step)
                                            ])
                                            theory.writeClause([
                                                '-push_t(box{},{}_{},{}_{},{}_{},{})'.format(box_id+1,player_x,player_y,from_x,from_y,to_x,to_y,step),
                                                'at(box{},{}_{},{})'.format(box_id+1,to_x,to_y,step)
                                            ])
                                            theory.writeClause([
                                                '-push_t(box{},{}_{},{}_{},{}_{},{})'.format(box_id+1,player_x,player_y,from_x,from_y,to_x,to_y,step),
                                                'empty({}_{},{})'.format(player_x,player_y,step)
                                            ])
                                            theory.writeClause([
                                                '-push_t(box{},{}_{},{}_{},{}_{},{})'.format(box_id+1,player_x,player_y,from_x,from_y,to_x,to_y,step),
                                                'in_target(box{},{})'.format(box_id+1,step)
                                            ])
                                            # e-
                                            theory.writeClause([
                                                '-push_t(box{},{}_{},{}_{},{}_{},{})'.format(box_id+1,player_x,player_y,from_x,from_y,to_x,to_y,step),
                                                '-empty({}_{},{})'.format(to_x,to_y,step)
                                            ])
                                            theory.writeClause([
                                                '-push_t(box{},{}_{},{}_{},{}_{},{})'.format(box_id+1,player_x,player_y,from_x,from_y,to_x,to_y,step),
                                                '-player({}_{},{})'.format(player_x,player_y,step)
                                            ])
                                            theory.writeClause([
                                                '-push_t(box{},{}_{},{}_{},{}_{},{})'.format(box_id+1,player_x,player_y,from_x,from_y,to_x,to_y,step),
                                                '-at(box{},{}_{},{})'.format(box_id+1,from_x,from_y,step)
                                            ])

    def encode_actions(self, theory, step):
        actions = []
        for fromXY in self.coords:
            for toXY in self.coords:
                if self.is_adjacent(fromXY, toXY):
                    actions.append(self.move(fromXY, toXY, step))
        for box_id in range(len(self.map_data['boxes'])):
            for playerXY in self.coords:
                for fromXY in self.coords:
                    for toXY in self.coords:
                        if self.is_inline(playerXY, fromXY, toXY):
                            actions.append(self.push(box_id+1, playerXY, fromXY, toXY, step))
                            actions.append(self.push_t(box_id+1, playerXY, fromXY, toXY, step))
        
        theory.writeComment('At least one action happens')
        theory.writeClause(actions)
        theory.writeComment('Action exclusivity')
        for action1 in range(len(actions)):
            for action2 in range(len(actions)):
                if action1 != action2:
                    theory.writeClause([self.neg(actions[action1]), self.neg(actions[action2])])

    def encodeGoal(self, w, N):
        w.writeComment('Goal')
        for box_id in range(len(self.map_data['boxes'])):
            w.writeLiteral(self.in_target(box_id+1, N))
            w.finishClause()
    
    def encodeInitState(self, theory):
        theory.writeComment('Initial state loaded from the map')
        theory.writeComment('Targets on the map (fact)')
        for XY in self.coords:
            if XY in self.map_data['targets']:
                theory.writeLiteral(self.target(XY))
            else:
                theory.writeLiteral(self.neg(self.target(XY)))
            theory.finishClause()
        theory.writeComment('Initial position of the player loaded from the map')
        for XY in self.coords:
            if XY == self.map_data['sokoban']:
                theory.writeLiteral(self.player(XY, 0))
            else:
                theory.writeLiteral(self.neg(self.player(XY, 0)))
            theory.finishClause()
        theory.writeComment('Initial boxes position loaded from the map')
        for XY in self.coords:
            for index,box in enumerate(self.map_data['boxes']):
                if XY == box:
                    theory.writeLiteral(self.at(index+1, XY, 0))
                else:
                    theory.writeLiteral(self.neg(self.at(index+1, XY, 0)))
                theory.finishClause()
        theory.writeComment('Boxes in the target')
        for index, box in enumerate(self.map_data['boxes']):
            if box in self.map_data['targets']:
                theory.writeLiteral(self.in_target(index+1, 0))
            else:
                theory.writeLiteral(self.neg(self.in_target(index+1, 0)))
            theory.finishClause()
        theory.writeComment('Initial empty squares loaded from the map')
        for XY in self.coords:
            if (XY not in self.map_data['walls'] and 
                XY not in self.map_data['boxes'] and 
                XY != self.map_data['sokoban']):
                theory.writeLiteral(self.empty(XY, 0))
            else:
                theory.writeLiteral(self.neg(self.empty(XY, 0)))
            theory.finishClause()

    def push(self, box_id, playerXY, fromXY, toXY, step):
        return ('push(box{},{}_{},{}_{},{}_{},{})'
                        .format(box_id, playerXY[0], playerXY[1], fromXY[0], fromXY[1], toXY[0], toXY[1], step))

    def push_t(self, box_id, playerXY, fromXY, toXY, step):
        return ('push_t(box{},{}_{},{}_{},{}_{},{})'
                        .format(box_id, playerXY[0], playerXY[1], fromXY[0], fromXY[1], toXY[0], toXY[1], step))

    def move(self, fromXY, toXY, step):
        return 'move({}_{},{}_{},{})'.format(fromXY[0], fromXY[1], toXY[0], toXY[1], step)

    def empty(self, XY, step):
        return 'empty({}_{},{})'.format(XY[0], XY[1], step)

    def player(self, XY, step):
        return 'player({}_{},{})'.format(XY[0], XY[1], step)

    def at(self, box_id, XY, step):
        return 'at(box{},{}_{},{})'.format(box_id, XY[0], XY[1], step)

    def target(self, XY):
        return 'target({}_{})'.format(XY[0], XY[1])

    def in_target(self, box_id, step):
        return 'in_target(box{},{})'.format(box_id, step)

    def neg(self, predicate):
        return '-' + predicate

    def load_map(self, file_name):
        self.map_data = {
            'map_size': (),
            'walls': [],
            'sokoban': (),
            'boxes': [],
            'targets': []
        }
        with open(file_name) as f:
            l = 0
            for line in f:
                ch = 0
                for char in line:
                    if char == '#':
                        self.map_data['walls'].append((l,ch))
                    elif char == 'S':
                        self.map_data['sokoban'] = (l,ch)
                    elif char == 'X':
                        self.map_data['sokoban'] = (l,ch)
                        self.map_data['targets'].append((l,ch))
                    elif char == 'B':
                        self.map_data['boxes'].append((l,ch))
                    elif char == 'T':
                        self.map_data['targets'].append((l,ch))
                    ch += 1 
                l += 1
            self.map_data['map_size'] = (l,ch)
    
    def generate_coords(self):
        coords = []
        for x in range(self.map_data['map_size'][0]):
            for y in range(self.map_data['map_size'][1]):
                coords.append((x,y))
        return coords

    def is_inline(self, playerXY, fromXY, toXY):
        if not self.is_adjacent(fromXY, toXY) or not self.is_adjacent(playerXY, fromXY):
            return False
        if fromXY[0] == toXY[0]:
            return fromXY[0] == playerXY[0]
        if fromXY[1] == toXY[1]:
            return fromXY[1] == playerXY[1]
        return False

    def is_adjacent(self, c1, c2):
        if c1 == c2:
            return False
        if c1[0] == c2[0] and c1[1] == c2[1]+1:
            return True
        if c1[0] == c2[0] and c1[1] == c2[1]-1:
            return True
        if c1[1] == c2[1] and c1[0] == c2[0]+1:
            return True
        if c1[1] == c2[1] and c1[0] == c2[0]-1:
            return True
        return False

ss = SokobanSolver('maps/map0.txt')
ss.solve()
