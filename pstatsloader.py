"""Module to load cProfile/profile records as a tree of records"""
import pstats, os

class PStatsLoader( object ):
    """Load profiler statistic from """
    def __init__( self, filename ):
        self.filename = filename 
        self.rows = {}
        self.stats = pstats.Stats( filename )
        self.tree = self.load( self.stats.stats )
        #self.location_tree = self.load_location( )
    def load( self, stats ):
        """Build a squaremap-compatible model from a pstats class"""
        rows = self.rows
        for func, raw in stats.iteritems():
            rows[func] =  PStatRow( func,raw )
        for row in rows.itervalues():
            row.weave( rows )
        for key,value in rows.items():
            if not value.parents:
                return value
        raise RuntimeError( 'No top-level function???' )
    def load_location( self ):
        """Build a squaremap-compatible model for location-based hierarchy"""
        directories = {}
        files = {}
        root = PStatLocation( '/', 'PYTHONPATH' )
        for child in self.rows.values():
            current = directories.get( child.directory )
            if current is None:
                directory, filename = child.directory, child.filename
                if directory == '':
                    current = root
                else:
                    current = PStatLocation( directory, 'package' )
                directories[ directory ] = current 
            file_current = files.get( (directory,filename) )
            current.children.append( child )
        # now link the directories...
        for key,value in directories.items():
            found = False
            while key:
                new_key,rest = os.path.split( key )
                if new_key == key:
                    break
                key = new_key
                parent = directories.get( key )
                if parent:
                    if value is not parent:
                        parent.children.append( value )
                        print '%s as parent of %s'%( parent, value )
                        found = True 
                        break 
            if not found:
                print 'adding to root', value
                if value is not root:
                    root.children.append( value )
        # lastly, finalize all of the directory records...
        root.finalize()
        return root 
    
class PStatRow( object ):
    """Simulates a HotShot profiler record using PStats module"""
    def __init__( self, key, raw ):
        self.children = []
        self.parents = []
        file,line,func = self.key = key
        try:
            dirname,basename = os.path.dirname(file),os.path.basename(file)
        except ValueError, err:
            dirname = ''
            basename = file
        nc, cc, tt, ct, callers = raw
        (
            self.calls, self.recursive, self.local, self.localPer,
            self.cummulative, self.cummulativePer, self.directory,
            self.filename, self.name, self.lineno
        ) = (
            nc, 
            cc,
            tt,
            tt/cc,
            ct,
            ct/nc,
            dirname,
            basename,
            func,
            line,
        )
        self.callers = callers
    def __repr__( self ):
        return 'PStatRow( %r,%r,%r,%r, %s )'%(self.directory, self.filename, self.lineno, self.name, self.children)
    def add_child( self, child ):
        self.children.append( child )
    
    def weave( self, rows ):
        for caller,data in self.callers.iteritems():
            # data is (cc,nc,tt,ct)
            parent = rows.get( caller )
            if parent:
                self.parents.append( parent )
                parent.children.append( self )
    def child_cumulative_time( self, child ):
        total = self.cummulative
        if total:
            (cc,nc,tt,ct) = child.callers[ self.key ]
            return float(ct)/total
        return 0

class PStatLocation( PStatRow ):
    """A row that represents a hierarchic structure other than call-patterns
    
    This is used to create a file-based hierarchy for the views
    
    Children with the name <module> are our "empty" space,
    our totals are otherwise just the sum of our children.
    """
    def __init__( self, directory, filename):
        self.directory = directory
        self.filename = filename
        self.name = ''
        self.children = []
    def __repr__( self ):
        return 'PStatLocation( %r,%r )'%(self.directory, self.filename)
    def finalize( self, already_done=None ):
        if already_done is None:
            already_done = {}
        if already_done.has_key( self ):
            return True 
        already_done[self] = True
        children = self.children
        real_children = []
        local_children = []
        for child in children:
            if hasattr( child, 'finalize' ):
                child.finalize( already_done)
            if child.name == '<module>':
                local_children.append( child )
            else:
                real_children.append( child )
        for field in ('recursive','cummulative'):
            value = sum([ getattr( child, field, 0 ) for child in children] )
            setattr( self, field, value )
        if self.recursive:
            self.cummulativePer = self.cummulative/float(self.recursive)
        else:
            self.recursive = 0
        if local_children:
            for field in ('local','calls'):
                value = sum([ getattr( child, field, 0 ) for child in children] )
                setattr( self, field, value )
            if self.calls:
                self.localPer = self.local / self.calls 
        else:
            self.local = 0
        self.children = real_children


if __name__ == "__main__":
    import sys
    p = PStatsLoader( sys.argv[1] )
    assert p.tree
    print p.tree