import subprocess
from lib.theoryWriter import TheoryWriter
import lib.text2dimacs

class SokobanSolver(object):

    MINISAT_PATH = 'lib/minisat/win/minisat.exe'
    CNF_FILE = 'cnf.txt'
    DIMACS_FILE = 'dimacs.txt'
    DIMACS_VARS_FILE = 'variables.txt'
    MINISAT_OUT_FILE = 'out.txt'

    def __init__(self, map_name):
        self.map_data = {}
        self.load_map(map_name)
        self.coords = self.generate_coords()

    def solve(self):
        ok = False
        iteration = 1
        sol = []
        while not ok:
            print('ITERATION:', iteration)
            theory = TheoryWriter(self.CNF_FILE)
            print('Writing theory ...')
            self.encode(theory, iteration)
            theory.close()
            print('Translating to DIMACS ...')
            lib.text2dimacs.translate(self.CNF_FILE, self.DIMACS_FILE)
            print('Solving ...')
            args = (self.MINISAT_PATH, self.DIMACS_FILE, self.MINISAT_OUT_FILE)
            popen = subprocess.Popen(args, stdout=subprocess.PIPE)
            popen.wait()
            ok, sol = self.spracuj()
            iteration += 1
        print('DONE')
        for x in sol:
            print(x)

    def spracuj(self):
        line = ''
        with open(self.MINISAT_OUT_FILE) as f:
            sat = f.readline().strip()
            if sat == 'UNSAT':
                return (False, [])
            line = f.readline().strip()
        minisat_vars = line.split()
        predicates = {}
        var = 0
        res = []
        with open(self.DIMACS_VARS_FILE) as f:
            for l in f:
                if var == 0:
                    var = int(l)
                else:
                    predicates[var] = l.strip()
                    var = 0
        for v in minisat_vars:
            v_int = int(v)
            if v_int > 0:
                pred = predicates.get(v_int, 'null')
                if (pred.startswith('move') or pred.startswith('push') or pred.startswith('push_t')):
                    res.append(pred)
        return (True, res)

    def encode(self, theory, iteration):
        self.encode_goal(theory, iteration)
        self.encodeInitState(theory)
        theory.writeComment('RULES')
        for step in range(1, iteration + 1):
            theory.writeComment('Na jednom policku moze byt bud hrac alebo nic alebo nejaky z boxov')
            theory.writeComment('Na polickach kde je stena nemoze byt hrac ani box - su stale ne-prazdne')
            for XY in self.coords:
                if self.not_wall(XY):
                    clause = [self.empty(XY, step), self.player(XY, step)]
                    for box_id in range(len(self.map_data['boxes'])):
                        clause.append(self.at(box_id+1, XY, step))
                    theory.writeClause(clause)
                else:
                    theory.writeClause([self.neg(self.empty(XY, step))])
            self.player_exlusivity(theory, step)
            self.box_exclusivity(theory, step)
            self.position_exclusivity(theory, step)
            self.actions(theory, step)

    def box_exclusivity(self, theory, step):
        theory.writeComment('Ak je box na nejakej pozicii, nemoze byt zaroven na druhej pozicii')
        for box_id in range(len(self.map_data['boxes'])):
            for c1 in range(len(self.coords)):
                for c2 in range(c1+1, len(self.coords)):
                    if self.not_wall(self.coords[c1], self.coords[c2]):
                        theory.writeClause([
                            self.neg(self.at(box_id+1, self.coords[c1], step)),
                            self.neg(self.at(box_id+1, self.coords[c2], step))
                        ])

    def player_exlusivity(self, theory, step):
        theory.writeComment('Ak je hrac na nejakej pozicii, nemoze byt zaroven na druhej pozicii')
        for c1 in range(len(self.coords)):
            for c2 in range(c1 + 1, len(self.coords)):
                if self.not_wall(self.coords[c1], self.coords[c2]):
                    theory.writeClause([
                        self.neg(self.player(self.coords[c1], step)),
                        self.neg(self.player(self.coords[c2], step))
                    ])

    def position_exclusivity(self, theory, step):
        theory.writeComment('Na jednom policku moze byt maximalne bud hrac, nic, box')
        for XY in self.coords:
            if self.not_wall(XY):
                theory.writeClause([self.neg(self.player(XY, step)), self.neg(self.empty(XY, step))])
                for box_id in range(len(self.map_data['boxes'])):
                    theory.writeClause([self.neg(self.player(XY, step)), self.neg(self.at(box_id+1, XY, step))])
                    theory.writeClause([self.neg(self.empty(XY, step)), self.neg(self.at(box_id+1, XY, step))])

    def actions(self, theory, step):
        self.action_move(theory, step)
        self.action_push(theory, step)
        self.action_push_t(theory, step)
        actions = []
        for fromXY in self.coords:
            for toXY in self.coords:
                if self.is_adjacent(fromXY, toXY) and self.not_wall(fromXY, toXY):
                    actions.append(self.move(fromXY, toXY, step))
        for box_id in range(len(self.map_data['boxes'])):
            for playerXY in self.coords:
                for fromXY in self.coords:
                    for toXY in self.coords:
                        if self.is_inline(playerXY, fromXY, toXY) and self.not_wall(playerXY, fromXY, toXY):
                            actions.append(self.push(box_id+1, playerXY, fromXY, toXY, step))
                            actions.append(self.push_t(box_id+1, playerXY, fromXY, toXY, step))
        theory.writeComment('At least one action happens')
        theory.writeClause(actions)
        theory.writeComment('Actions exclusivity')
        for action1 in range(len(actions)):
            for action2 in range(action1+1, len(actions)):
                if action1 != action2:
                    theory.writeClause([self.neg(actions[action1]), self.neg(actions[action2])])

    def action_move(self, theory, step):
        theory.writeComment('Action move(fromXY, toXY, step)')
        for fromXY in self.coords:
            for toXY in self.coords:
                if self.is_adjacent(fromXY, toXY) and self.not_wall(fromXY, toXY):
                    # P+
                    theory.writeClause([
                        self.neg(self.move(fromXY, toXY, step)),
                        self.player(fromXY, step-1)
                    ])
                    theory.writeClause([
                        self.neg(self.move(fromXY, toXY, step)),
                        self.empty(toXY, step-1)
                    ])
                    # E+
                    theory.writeClause([
                        self.neg(self.move(fromXY, toXY, step)),
                        self.player(toXY, step)
                    ])
                    theory.writeClause([
                        self.neg(self.move(fromXY, toXY, step)),
                        self.empty(fromXY, step)
                    ])
                    # E-
                    for box_id in range(len(self.map_data['boxes'])):
                        theory.writeClause([
                            self.neg(self.move(fromXY, toXY, step)),
                            self.neg(self.in_target(box_id+1, step))
                        ])
                    # theory.writeClause([
                    #     self.neg(self.move(fromXY, toXY, step)),
                    #     self.neg(self.empty(toXY, step))
                    # ])
                    # theory.writeClause([
                    #     self.neg(self.move(fromXY, toXY, step)),
                    #     self.neg(self.player(fromXY, step))
                    # ])
                    # for box_id in range(len(self.map_data['boxes'])):
                    #     theory.writeClause([
                    #         self.neg(self.move(fromXY, toXY, step)),
                    #         self.neg(self.at(box_id+1, fromXY, step))
                    #     ])

    def action_push(self, theory, step):
        theory.writeComment('Action push(box, playerXY, fromXY, toXY, step)')
        for box_id in range(len(self.map_data['boxes'])):
            for playerXY in self.coords:
                for fromXY in self.coords:
                    for toXY in self.coords:
                        if self.is_inline(playerXY, fromXY, toXY) and self.not_wall(playerXY, fromXY, toXY):
                            # P+
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
                            # P-
                            theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.target(toXY))
                            ])
                            # E+
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
                            # E-
                            # theory.writeClause([
                            #     self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                            #     self.neg(self.empty(toXY, step))
                            # ])
                            # theory.writeClause([
                            #     self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                            #     self.neg(self.player(playerXY, step))
                            # ])
                            # theory.writeClause([
                            #     self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                            #     self.neg(self.at(box_id+1, fromXY, step))
                            # ])
                            theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.in_target(box_id+1, step))
                            ])
                            theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.in_target(box_id+1, step-1))
                            ])

    def action_push_t(self, theory, step):
        theory.writeComment('Action push_t(box, playerXY, fromXY, toXY, step)')
        for box_id in range(len(self.map_data['boxes'])):
            for playerXY in self.coords:
                for fromXY in self.coords:
                    for toXY in self.coords:
                        if self.is_inline(playerXY, fromXY, toXY) and self.not_wall(playerXY, fromXY, toXY):
                            # P+
                            theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.empty(toXY, step-1)
                            ])
                            theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.player(playerXY, step-1)
                            ])
                            theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.at(box_id+1, fromXY, step-1)
                            ])
                            theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.target(toXY)
                            ])
                            theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.in_target(box_id+1, step-1))
                            ])
                            # E+
                            theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.player(fromXY, step)
                            ])
                            theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.at(box_id+1, toXY, step)
                            ])
                            theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.empty(playerXY, step)
                            ])
                            theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.in_target(box_id+1, step)
                            ])
                            # E-
                            for box_id2 in range(len(self.map_data['boxes'])):
                                if box_id != box_id2:
                                    theory.writeClause([
                                        self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                        self.neg(self.in_target(box_id2+1, step))
                                    ])
                            # theory.writeClause([
                            #     self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                            #     self.neg(self.player(playerXY, step))
                            # ])
                            # theory.writeClause([
                            #     self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                            #     self.neg(self.at(box_id+1, fromXY, step))
                            # ])

    def encode_goal(self, theory, N):
        theory.writeComment('Goal')
        theory.writeClause([self.goal(N)])
        theory.writeComment('Goal rules')
        for box_id in range(len(self.map_data['boxes'])):
            clause = [self.neg(self.goal(N))]
            for i in range(N+1):
                clause.append(self.in_target(box_id+1, i))
            theory.writeClause(clause)

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
            for index, box in enumerate(self.map_data['boxes']):
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

    def goal(self, N):
        return 'goal({})'.format(N)

    def wall(self, XY):
        return 'wall({}_{})'.format(XY[0], XY[1])

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
                        self.map_data['walls'].append((l, ch))
                    elif char == 'S':
                        self.map_data['sokoban'] = (l, ch)
                    elif char == 'X':
                        self.map_data['sokoban'] = (l, ch)
                        self.map_data['targets'].append((l, ch))
                    elif char == 'B':
                        self.map_data['boxes'].append((l, ch))
                    elif char == 'T':
                        self.map_data['targets'].append((l, ch))
                    ch += 1
                l += 1
            self.map_data['map_size'] = (l, ch)

    def generate_coords(self):
        coords = []
        for x in range(self.map_data['map_size'][0]):
            for y in range(self.map_data['map_size'][1]):
                coords.append((x, y))
        return coords

    def is_inline(self, playerXY, fromXY, toXY):
        if not self.is_adjacent(fromXY, toXY) or not self.is_adjacent(playerXY, fromXY) or playerXY == toXY:
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

    def not_wall(self, *coords):
        for coord in coords:
            if coord in self.map_data['walls']:
                return False
        return True


if __name__ == "__main__":
    ss = SokobanSolver('maps/map3.txt')
    ss.solve()
