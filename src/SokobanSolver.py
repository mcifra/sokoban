import subprocess
from lib.theoryWriter import TheoryWriter
import lib.text2dimacs

class SokobanSolver(object):

    MINISAT_PATH = 'lib/minisat/win/minisat.exe'
    CNF_FILE = 'cnf.txt'
    DIMACS_FILE = 'dimacs.txt'
    DIMACS_VARS_FILE = 'variables.txt'
    MINISAT_OUT_FILE = 'out.txt'
    LIMIT = 10

    def __init__(self, map_name):
        self.map_name = map_name
        self.map_data = {}
        self.load_map(map_name)
        self.coords = self.generate_coords()
        self.theory = TheoryWriter(self.CNF_FILE)
    
    def set_limit(self, limit):
        self.LIMIT = limit

    def solve(self):
        solution_found = False
        iteration = 1
        solution = []
        while not solution_found and iteration <= self.LIMIT:
            print('> ITERATION: {}'.format(iteration))
            print('Writing theory ...')
            self.encode_iteration(iteration)
            print('Translating to DIMACS ...')
            self.translate_to_dimacs()
            print('Solving ...')
            self.run_minisat()
            solution_found, solution = self.process_solution()
            iteration += 1
        self.theory.close()
        print('DONE')
        if solution_found:
            print('Solution found, actions:')
            for action in solution:
                print(action)
        else:
            print('Solution not found. Limit of steps reached ({})'.format(self.LIMIT))

    def run_minisat(self):
        args = (self.MINISAT_PATH, self.DIMACS_FILE, self.MINISAT_OUT_FILE)
        popen = subprocess.Popen(args, stdout=subprocess.PIPE)
        popen.wait()

    def translate_to_dimacs(self):
        lib.text2dimacs.translate(self.CNF_FILE, self.DIMACS_FILE)

    def process_solution(self):
        output = ''
        with open(self.MINISAT_OUT_FILE) as f:
            sat = f.readline().strip()
            if sat == 'UNSAT':
                return (False, [])
            output = f.readline().strip()
        minisat_vars = output.split()
        predicates = {}
        var = 0
        res = []
        with open(self.DIMACS_VARS_FILE) as f:
            for line in f:
                line = line.strip()
                if var == 0:
                    var = int(line)
                    continue
                predicates[var] = line
                var = 0
        for v in minisat_vars:
            v_int = int(v)
            if v_int > 0:
                pred = predicates.get(v_int, 'null')
                if (pred.startswith('move') or pred.startswith('push') or pred.startswith('push_t')):
                    res.append(pred)
        return (True, res)

    def encode_iteration(self, iteration):
        self.theory.new_iteration()
        self.theory.writeComment('Map: {}'.format(self.map_name))
        self.encode_goal(iteration)
        self.encode_init_state()
        for step in range(1, iteration+1):
            self.theory.writeComment('RULES - STEP {}'.format(step))
            self.theory.writeComment('Na jednom policku moze byt bud hrac alebo nic alebo nejaky z boxov')
            self.theory.writeComment('Na polickach kde je stena nemoze byt hrac ani box - su stale ne-prazdne')
            for XY in self.coords:
                if self.not_wall(XY):
                    clause = [self.empty(XY, step), self.player(XY, step)]
                    for box_id in range(len(self.map_data['boxes'])):
                        clause.append(self.at(box_id+1, XY, step))
                    self.theory.writeClause(clause)
                else:
                    self.theory.writeClause([self.neg(self.empty(XY, step))])
            self.player_exlusivity(step)
            self.box_exclusivity(step)
            self.position_exclusivity(step)
            self.actions(step)

    def box_exclusivity(self, step):
        self.theory.writeComment('Ak je box na nejakej pozicii, nemoze byt zaroven na druhej pozicii')
        for box_id in range(len(self.map_data['boxes'])):
            for c1 in range(len(self.coords)):
                for c2 in range(c1+1, len(self.coords)):
                    if self.not_wall(self.coords[c1], self.coords[c2]):
                        self.theory.writeClause([
                            self.neg(self.at(box_id+1, self.coords[c1], step)),
                            self.neg(self.at(box_id+1, self.coords[c2], step))
                        ])

    def player_exlusivity(self, step):
        self.theory.writeComment('Ak je hrac na nejakej pozicii, nemoze byt zaroven na druhej pozicii')
        for c1 in range(len(self.coords)):
            for c2 in range(c1 + 1, len(self.coords)):
                if self.not_wall(self.coords[c1], self.coords[c2]):
                    self.theory.writeClause([
                        self.neg(self.player(self.coords[c1], step)),
                        self.neg(self.player(self.coords[c2], step))
                    ])

    def position_exclusivity(self, step):
        self.theory.writeComment('Na jednom policku moze byt maximalne bud hrac, nic, box')
        for XY in self.coords:
            if self.not_wall(XY):
                self.theory.writeClause([self.neg(self.player(XY, step)), self.neg(self.empty(XY, step))])
                for box_id in range(len(self.map_data['boxes'])):
                    self.theory.writeClause([self.neg(self.player(XY, step)), self.neg(self.at(box_id+1, XY, step))])
                    self.theory.writeClause([self.neg(self.empty(XY, step)), self.neg(self.at(box_id+1, XY, step))])

    def actions(self, step):
        self.action_move(step)
        self.action_push(step)
        self.action_push_t(step)
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
        self.theory.writeComment('At least one action happens')
        self.theory.writeClause(actions)
        self.theory.writeComment('Actions exclusivity')
        for action1 in range(len(actions)):
            for action2 in range(action1+1, len(actions)):
                if action1 != action2:
                    self.theory.writeClause([self.neg(actions[action1]), self.neg(actions[action2])])
        self.frame_problem(step)

    def action_move(self, step):
        self.theory.writeComment('Action move(fromXY, toXY, step)')
        for fromXY in self.coords:
            for toXY in self.coords:
                if self.is_adjacent(fromXY, toXY) and self.not_wall(fromXY, toXY):
                    # P+
                    self.theory.writeClause([
                        self.neg(self.move(fromXY, toXY, step)),
                        self.player(fromXY, step-1)
                    ])
                    self.theory.writeClause([
                        self.neg(self.move(fromXY, toXY, step)),
                        self.empty(toXY, step-1)
                    ])
                    # E+
                    self.theory.writeClause([
                        self.neg(self.move(fromXY, toXY, step)),
                        self.player(toXY, step)
                    ])
                    self.theory.writeClause([
                        self.neg(self.move(fromXY, toXY, step)),
                        self.empty(fromXY, step)
                    ])

    def action_push(self, step):
        self.theory.writeComment('Action push(box, playerXY, fromXY, toXY, step)')
        for box_id in range(len(self.map_data['boxes'])):
            for playerXY in self.coords:
                for fromXY in self.coords:
                    for toXY in self.coords:
                        if self.is_inline(playerXY, fromXY, toXY) and self.not_wall(playerXY, fromXY, toXY):
                            # P+
                            self.theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.empty(toXY, step-1)
                            ])
                            self.theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.player(playerXY, step-1)
                            ])
                            self.theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.at(box_id+1, fromXY, step-1)
                            ])
                            # P-
                            self.theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.target(toXY))
                            ])
                            # E+
                            self.theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.player(fromXY, step)
                            ])
                            self.theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.at(box_id+1, toXY, step)
                            ])
                            self.theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.empty(playerXY, step)
                            ])
                            self.theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.in_target(box_id+1, step))
                            ])
                            

    def action_push_t(self, step):
        self.theory.writeComment('Action push_t(box, playerXY, fromXY, toXY, step)')
        for box_id in range(len(self.map_data['boxes'])):
            for playerXY in self.coords:
                for fromXY in self.coords:
                    for toXY in self.coords:
                        if self.is_inline(playerXY, fromXY, toXY) and self.not_wall(playerXY, fromXY, toXY):
                            # P+
                            self.theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.empty(toXY, step-1)
                            ])
                            self.theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.player(playerXY, step-1)
                            ])
                            self.theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.at(box_id+1, fromXY, step-1)
                            ])
                            self.theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.target(toXY)
                            ])
                            # P-
                            self.theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.in_target(box_id+1, step-1))
                            ])
                            # E+
                            self.theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.player(fromXY, step)
                            ])
                            self.theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.at(box_id+1, toXY, step)
                            ])
                            self.theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.empty(playerXY, step)
                            ])
                            self.theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.in_target(box_id+1, step)
                            ])

    def frame_problem(self, step):
        self.theory.writeComment('Frame 1 - ak sa hrac posunie, nezmeni sa poloha boxov')
        self.theory.writeComment('Frame 2 - ak sa hrac posunie, boxy ktore boli/neboli v cieli zostanu/nebudu v cieli')
        for box_id in range(len(self.map_data['boxes'])):
            for boxXY in self.coords:
                for fromXY in self.coords:
                    for toXY in self.coords:
                        if self.is_adjacent(fromXY, toXY) and self.not_wall(boxXY, fromXY, toXY):
                            self.theory.writeClause([
                                self.neg(self.at(box_id+1, boxXY, step-1)),
                                self.neg(self.move(fromXY, toXY, step)),
                                self.at(box_id+1, boxXY, step)
                            ])
                            self.theory.writeClause([
                                self.neg(self.in_target(box_id+1, step-1)),
                                self.neg(self.move(fromXY, toXY, step)),
                                self.in_target(box_id+1, step),
                            ])
                            self.theory.writeClause([
                                self.in_target(box_id+1, step-1),
                                self.neg(self.move(fromXY, toXY, step)),
                                self.neg(self.in_target(box_id+1, step)),
                            ])
        self.theory.writeComment('Frame 3 - ak sa posunie nejaky box, ostatne boxy sa neposunu')
        self.theory.writeComment('Frame 4 - ak sa posunie nejaky box, a ak nejaky iny je/nieje v cieli tak zostane/nebude v cieli')
        for box_id in range(len(self.map_data['boxes'])):
            for boxXY in self.coords:
                for box_id2 in range(len(self.map_data['boxes'])):
                    if box_id != box_id2:
                        for playerXY in self.coords:
                            for fromXY in self.coords:
                                for toXY in self.coords:
                                    if self.is_inline(playerXY, fromXY, toXY) and self.not_wall(boxXY, playerXY, fromXY, toXY):
                                        self.theory.writeClause([
                                            self.neg(self.at(box_id+1, boxXY, step-1)),
                                            self.neg(self.push(box_id2+1, playerXY, fromXY, toXY, step)),
                                            self.at(box_id+1, boxXY, step)
                                        ])
                                        self.theory.writeClause([
                                            self.neg(self.at(box_id+1, boxXY, step-1)),
                                            self.neg(self.push_t(box_id2+1, playerXY, fromXY, toXY, step)),
                                            self.at(box_id+1, boxXY, step)
                                        ])
                                        self.theory.writeClause([
                                            self.neg(self.in_target(box_id+1, step-1)),
                                            self.neg(self.push(box_id2+1, playerXY, fromXY, toXY, step)),
                                            self.in_target(box_id+1, step)
                                        ])
                                        self.theory.writeClause([
                                            self.neg(self.in_target(box_id+1, step-1)),
                                            self.neg(self.push_t(box_id2+1, playerXY, fromXY, toXY, step)),
                                            self.in_target(box_id+1, step)
                                        ])
                                        self.theory.writeClause([
                                            self.in_target(box_id+1, step-1),
                                            self.neg(self.push(box_id2+1, playerXY, fromXY, toXY, step)),
                                            self.neg(self.in_target(box_id+1, step))
                                        ])
                                        self.theory.writeClause([
                                            self.in_target(box_id+1, step-1),
                                            self.neg(self.push_t(box_id2+1, playerXY, fromXY, toXY, step)),
                                            self.neg(self.in_target(box_id+1, step))
                                        ])


    def encode_goal(self, step):
        self.theory.writeComment('Goal')
        for box_id in range(len(self.map_data['boxes'])):
            self.theory.writeClause([self.in_target(box_id+1, step)])

    def encode_init_state(self):
        self.theory.writeComment('Initial state loaded from the map')
        self.theory.writeComment('Targets on the map (fact)')
        for XY in self.coords:
            if XY in self.map_data['targets']:
                self.theory.writeLiteral(self.target(XY))    
            else:
                self.theory.writeLiteral(self.neg(self.target(XY)))
            self.theory.finishClause()
        self.theory.writeComment('Initial position of the player loaded from the map')
        for XY in self.coords:
            if XY == self.map_data['sokoban']:
                self.theory.writeLiteral(self.player(XY, 0))
            else:
                self.theory.writeLiteral(self.neg(self.player(XY, 0)))
            self.theory.finishClause()
        self.theory.writeComment('Initial boxes position loaded from the map')
        for XY in self.coords:
            for index, box in enumerate(self.map_data['boxes']):
                if XY == box:
                    self.theory.writeLiteral(self.at(index+1, XY, 0))
                else:
                    self.theory.writeLiteral(self.neg(self.at(index+1, XY, 0)))
                self.theory.finishClause()
        self.theory.writeComment('Boxes in the target')
        for index, box in enumerate(self.map_data['boxes']):
            if box in self.map_data['targets']:
                self.theory.writeLiteral(self.in_target(index+1, 0))
            else:
                self.theory.writeLiteral(self.neg(self.in_target(index+1, 0)))
            self.theory.finishClause()
        self.theory.writeComment('Initial empty squares loaded from the map')
        for XY in self.coords:
            if (XY not in self.map_data['walls'] and
                XY not in self.map_data['boxes'] and
                    XY != self.map_data['sokoban']):
                self.theory.writeLiteral(self.empty(XY, 0))
            else:
                self.theory.writeLiteral(self.neg(self.empty(XY, 0)))
            self.theory.finishClause()

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
