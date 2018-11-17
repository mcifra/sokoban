class TheoryWriter(object):
    
    def __init__(self, filename):
        self.fn = filename
        self.f = open(filename, 'w')

    def new_iteration(self):
        if not self.closed():
            self.f.close()
        self.f = open(self.fn, 'w')

    def filename(self):
        """ Returns the filename that this writer writes to as a string."""
        return self.fn

    def writeLiteral(self, lit):
        """ Writes a single literal.

            Use finishClause to finis this clause (write a zero).
        """
        self.f.write('{} '.format(lit))

    def finishClause(self):
        """" Finishes current clause (writes a newline)."""
        self.f.write('\n')
        self.f.flush()

    def writeClause(self, clause):
        """ Writes a single clause.

            *clause* must be a list of literals.
        """
        for l in clause:
            self.writeLiteral(l)
        self.finishClause()

    def writeImpl(self, left, right):
        """ Writes an implication *left* => *right*. """
        self.writeClause(['-' + left, right])

    def writeComment(self, comment):
        """ Writes a comment.

            Note that this does not work inside an unfinished clause!
        """
        for line in comment.split('\n'):
            self.f.write('c {}\n'.format(line))

    def closed(self):
        """ Returs True if the output file has been already closed. """
        return self.f.closed

    def close(self):
        """ Closes the output file. """
        self.f.close()
