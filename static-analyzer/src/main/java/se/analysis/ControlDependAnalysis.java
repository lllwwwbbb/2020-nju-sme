package se.analysis;

import se.analysis.sourcemap.JStmt;
import se.analysis.sourcemap.JStmtRelationGraph;
import soot.Body;
import soot.Scene;
import soot.Trap;
import soot.Unit;
import soot.grimp.Grimp;
import soot.toolkits.graph.*;
import soot.toolkits.scalar.Pair;

import java.util.*;
import java.util.stream.Collectors;

public class ControlDependAnalysis implements JStmtRelationGraph {

    private Set<Pair<JStmt, JStmt>> stmtDepSet;

    public ControlDependAnalysis(Body body) {
        if (body.getTraps().size() == 0 && body.getUnits().stream().noneMatch(Unit::branches)) {
            stmtDepSet = Collections.emptySet();
            return;
        }
        Set<Pair<Unit, Unit>> unitDepSet = new HashSet<>();
        DirectedGraph<Unit> reversedGraph = new InverseGraph<>(new CustomUnitGraph(body));
        DominatorTree<Unit> dominatorTree = new DominatorTree<>(new MHGDominatorsFinder<>(reversedGraph));
        DominanceFrontier<Unit> dominanceFrontier = new CytronDominanceFrontier<>(dominatorTree);
        for (Unit u: body.getUnits()) {
            List<DominatorNode<Unit>> frontier = dominanceFrontier.getDominanceFrontierOf(dominatorTree.getDode(u));
            frontier.forEach(dominatorNode -> unitDepSet.add(new Pair<>(u, dominatorNode.getGode())));
        }
        stmtDepSet = JStmtRelationGraph.get(body.getMethod().getDeclaringClass(), unitDepSet);
    }

    @Override
    public Set<Pair<JStmt, JStmt>> getJStmtRelationSet() {
        return stmtDepSet;
    }

    /**
     * An unit graph base on ExceptionalUnitGraph, allow edge from excepting node to handler node,
     * eliminate edge from excepting node's predecessors to handler node, since the control is depend
     * on the execution of the excepting node but not the predecessors.
     */
    private static class CustomUnitGraph implements DirectedGraph<Unit> {

        private ExceptionalUnitGraph exGraph;
        private Map<Unit, List<Unit>> spPredsMap = new HashMap<>();
        private Map<Unit, List<Unit>> spSuccsMap = new HashMap<>();

        private CustomUnitGraph(Body body) {
            exGraph = new ExceptionalUnitGraph(body, Scene.v().getDefaultThrowAnalysis(), false);
            for (Trap trap: exGraph.getBody().getTraps()) {
                List<Unit> predsOfHandler = exGraph.getPredsOf(trap.getHandlerUnit());
                for (Unit unit: predsOfHandler) {
                    if (exGraph.getExceptionDests(unit).stream().anyMatch(
                            dest -> dest.getHandlerNode() == trap.getHandlerUnit()))
                        continue;
                    // remove edge from this unit to trap's handler
                    spSuccsMap.put(unit, exGraph.getSuccsOf(unit).stream().filter(
                            u -> u != trap.getHandlerUnit()
                    ).collect(Collectors.toList()));
                    spPredsMap.put(trap.getHandlerUnit(), predsOfHandler.stream().filter(
                            u -> u != unit
                    ).collect(Collectors.toList()));
                }
            }
        }

        @Override
        public List<Unit> getHeads() {
            return exGraph.getHeads();
        }

        @Override
        public List<Unit> getTails() {
            return exGraph.getTails();
        }

        @Override
        public List<Unit> getPredsOf(Unit unit) {
            return spPredsMap.getOrDefault(unit, exGraph.getPredsOf(unit));
        }

        @Override
        public List<Unit> getSuccsOf(Unit unit) {
            return spSuccsMap.getOrDefault(unit, exGraph.getSuccsOf(unit));
        }

        @Override
        public int size() {
            return exGraph.size();
        }

        @Override
        public Iterator<Unit> iterator() {
            return exGraph.iterator();
        }
    }
}
