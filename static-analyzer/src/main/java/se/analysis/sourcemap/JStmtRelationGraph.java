package se.analysis.sourcemap;

import soot.SootClass;
import soot.Unit;
import soot.toolkits.scalar.Pair;

import java.util.HashSet;
import java.util.Set;

public interface JStmtRelationGraph {

    Set<Pair<JStmt, JStmt>> getJStmtRelationSet();

    static Pair<JStmt, JStmt> getPair(SootClass sc, Unit u1, Unit u2) {
        JStmt s1 = JStmt.get(sc, u1);
        JStmt s2 = JStmt.get(sc, u2);
        if (s1 != null && s2 != null && !s1.equals(s2))
            return new Pair<>(s1, s2);
        return null;
    }

    static Set<Pair<JStmt, JStmt>> get(SootClass sc, Set<Pair<Unit, Unit>> unitPairSet) {
        Set<Pair<JStmt, JStmt>> stmtSet = new HashSet<>();
        unitPairSet.forEach(unitPair -> {
            Pair<JStmt, JStmt> stmtPair = getPair(sc, unitPair.getO1(), unitPair.getO2());
            if (stmtPair != null)
                stmtSet.add(stmtPair);
        });
        return stmtSet;
    }
}
