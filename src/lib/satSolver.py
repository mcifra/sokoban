import subprocess
import os
import sys

class SatSolver(object):
    """ A helper class that manages SAT solver invocation. """

    def __init__(self, solverPath = None):
        """ Creates a new SAT solver.

            Use *solverPath* to specify an optional location where to look
            for SAT solver binary (it will be looked for in a set of default
            locations).
        """

        # self.paths = []
        # if solverPath:
        #     self.paths.append(solverPath)

        # if sys.platform.startswith('linux'):
        #     self.paths += [
        #             'minisat', 'MiniSat_v1.14_linux',
        #             './minisat', './MiniSat_v1.14_linux',
        #             '../tools/lin/minisat'
        #         ]
        # elif sys.platform.startswith('win'):
        #     self.paths += [
        #             'minisat.exe', 'MiniSat_v1.14.exe',
        #             '../minisat/minisat.exe',
        #         ]
        # else:
        #     pass # empty solver paths will fall back to try 'minisat'

        # default fall for all
        # self.paths.append('minisat')

    def getSolverPath(self):
        return './win/minisat.exe'
        """ Returns the path to solver binary. """
        # for fn in self.paths:
        #     try:
        #         subprocess.check_output([fn, '--help'], stderr = subprocess.STDOUT)
        #         sys.stderr.write('using sat solver:  "%s"\n' % fn)
        #         return fn
        #     except OSError:
        #         pass
        # raise IOError('Solver executable not found!')

    def solve(self, theory_file, output_file):
        try:
            # self.output = subprocess.check_output(['./win/minisat.exe', theory_file, output_file])
            foo=subprocess.call(['minisat/win/minisat.exe', theory_file, output_file])
            print(foo)
        except subprocess.CalledProcessError:
            # minisat has weird return codes
            print('error: minisat has weird return codes')
            pass

        with open(output_file) as f:
            sat = f.readline()
            if sat.strip() == 'SAT':
                return True
                # sol = f.readline()
                # return (
                #         True,
                #         [int(x) for x in sol.split()][:-1]
                # )
            else:
                return False
                # return (False, [])


# vim: set sw=4 ts=4 sts=4 et :
