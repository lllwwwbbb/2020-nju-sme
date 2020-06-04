package se.analysis;

import se.analysis.sourcemap.JStmt;
import se.analysis.sourcemap.JStmtRelationGraph;
import soot.Body;
import soot.Scene;
import soot.SootMethod;
import soot.Unit;
import soot.toolkits.graph.ExceptionalUnitGraph;
import soot.toolkits.graph.MHGDominatorsFinder;
import soot.toolkits.scalar.Pair;

import java.util.HashSet;
import java.util.Set;

public class DominanceAnalysis implements JStmtRelationGraph {

    private Set<Pair<JStmt, JStmt>> stmtDominanceSet;

    public DominanceAnalysis(Body body) {
        MHGDominatorsFinder<Unit> finder = new MHGDominatorsFinder<>(
                new ExceptionalUnitGraph(body, Scene.v().getDefaultThrowAnalysis(), true));
        Set<Pair<Unit, Unit>> unitDominanceSet = new HashSet<>();
        for (Unit u: body.getUnits()) {
            Unit dominator = finder.getImmediateDominator(u);
            if (dominator != null)
                unitDominanceSet.add(new Pair<>(dominator, u));
        }
        stmtDominanceSet = JStmtRelationGraph.get(body.getMethod().getDeclaringClass(), unitDominanceSet);
    }

    @Override
    public Set<Pair<JStmt, JStmt>> getJStmtRelationSet() {
        return stmtDominanceSet;
    }
}
