package se.analysis.sourcemap;

import soot.SootClass;
import soot.SootMethod;
import soot.Unit;
import soot.Value;
import soot.jimple.internal.JCaughtExceptionRef;
import soot.jimple.internal.JIdentityStmt;

public class JStmt {

    private String className;
    private int lineno;

    private JStmt(String className, int lineno) {
        this.className = className;
        this.lineno = lineno;
    }

    static JStmt get(SootClass sootClass, Unit unit) {
        int lineno = unit.getJavaSourceStartLineNumber();
        if (lineno < 0)
            return null;
        if (isExceptionCaughtUnit(unit))
            return null;
        String className = sootClass.getName();
        return new JStmt(className, lineno);
    }

    private static boolean isExceptionCaughtUnit(Unit u) {
        if (!(u instanceof JIdentityStmt))
            return false;
        Value rightValue = ((JIdentityStmt) u).rightBox.getValue();
        return rightValue instanceof JCaughtExceptionRef;
    }

    @Override
    public boolean equals(Object obj) {
        return obj instanceof JStmt && this.toString().equals(obj.toString());
    }

    @Override
    public int hashCode() {
        return toString().hashCode();
    }

    @Override
    public String toString() {
        return className + "#" + lineno;
    }
}
