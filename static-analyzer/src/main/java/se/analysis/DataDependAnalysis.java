package se.analysis;

import se.analysis.sourcemap.JStmt;
import se.analysis.sourcemap.JStmtRelationGraph;
import soot.*;
import soot.jimple.InvokeExpr;
import soot.toolkits.graph.ExceptionalUnitGraph;
import soot.toolkits.scalar.ForwardFlowAnalysis;
import soot.toolkits.scalar.Pair;
import soot.util.Switch;

import java.util.*;


public class DataDependAnalysis extends ForwardFlowAnalysis<Unit, Map<CustomValue, Set<Unit>>>
        implements JStmtRelationGraph {

    private LinkedList<LinkedList<Pair<Value, Unit>>> depGraph = new LinkedList<>();
    private HashMap<Integer, Unit> idxUnitMap = new HashMap<>();

    private Set<Pair<JStmt, JStmt>> stmtDepSet = new HashSet<>();

    public DataDependAnalysis(Body body) {
        super(new ExceptionalUnitGraph(body, Scene.v().getDefaultThrowAnalysis(), true));
        doAnalysis();
        SootClass sc = body.getMethod().getDeclaringClass();
        int i = 0;
        for (LinkedList<Pair<Value, Unit>> depList: depGraph) {
            Unit u = idxUnitMap.get(i);
            for (Pair<Value, Unit> p: depList) {
                Pair<JStmt, JStmt> stmtDep = JStmtRelationGraph.getPair(sc, u, p.getO2());
                if (stmtDep != null)
                    stmtDepSet.add(stmtDep);
            }
            i += 1;
        }
    }

    @Override
    public Set<Pair<JStmt, JStmt>> getJStmtRelationSet() {
        return stmtDepSet;
    }

    protected Map<CustomValue, Set<Unit>> newInitialFlow() {
        return new HashMap<>();
    }

    protected void merge(Map<CustomValue, Set<Unit>> in1,  Map<CustomValue, Set<Unit>> in2,
                         Map<CustomValue, Set<Unit>> out) {
        out.putAll(in1);
        in2.forEach((v, set) -> {
            if (out.containsKey(v)) {
                Set<Unit> newSet = new HashSet<>(set);
                newSet.addAll(out.get(v));
                out.put(v, Collections.unmodifiableSet(newSet));
            } else {
                out.put(v, set);
            }
        });
    }

    protected void copy(Map<CustomValue, Set<Unit>> in, Map<CustomValue, Set<Unit>> out) {
        out.putAll(in);
    }

    protected void flowThrough(Map<CustomValue, Set<Unit>> in, Unit unit, Map<CustomValue, Set<Unit>> out) {
        // catch dependencies
        LinkedList<Pair<Value, Unit>> depList = new LinkedList<>();
        unit.getUseBoxes().forEach(vb -> {
            if (vb.getValue() instanceof InvokeExpr)
                return;
            Set<Unit> unitSet = in.getOrDefault(new CustomValue(vb.getValue()), Collections.emptySet());
            unitSet.forEach(u -> depList.addFirst(new Pair<>(vb.getValue(), u)));
        });
        updateDependence(unit, depList);

        // kill set & gen set
        out.putAll(in);
        unit.getDefBoxes().forEach(vb -> {
            // For example, Arr[0] is def at the same line as Arr, don't put Arr[0] into def-set anymore.
            if (vb.getValue().getUseBoxes().stream().map(ub -> new CustomValue(ub.getValue())).anyMatch(
                    cv -> out.getOrDefault(cv, Collections.emptySet()).stream().anyMatch(
                            u -> u.getJavaSourceStartLineNumber() == unit.getJavaSourceStartLineNumber()
                    )
            ))
                return;
            out.put(new CustomValue(vb.getValue()), Collections.singleton(unit));
        });
    }

    private void updateDependence(Unit u, LinkedList<Pair<Value, Unit>> depList) {
        if (depList.isEmpty())
            return;
        idxUnitMap.put(depGraph.size(), u);
        depGraph.addLast(depList);
    }
}

/**
 * An Custom Value class implements equals() & hashCode()
 */
class CustomValue implements Value{

    private final Value value;

    CustomValue(Value value) {
        this.value = value;
    }

    @Override
    public List<ValueBox> getUseBoxes() {
        return value.getUseBoxes();
    }

    @Override
    public Type getType() {
        return value.getType();
    }

    @Override
    public Object clone() {
        return new CustomValue(value);
    }

    @Override
    public void toString(UnitPrinter unitPrinter) {
        value.toString(unitPrinter);
    }

    @Override
    public boolean equivTo(Object o) {
        return value.equivTo(o);
    }

    @Override
    public int equivHashCode() {
        return value.equivHashCode();
    }

    @Override
    public void apply(Switch aSwitch) {
        value.apply(aSwitch);
    }

    @Override
    public boolean equals(Object obj) {
        if (obj instanceof CustomValue)
            return value.equivTo(((CustomValue) obj).value);
        return false;
    }

    @Override
    public int hashCode() {
        return value.equivHashCode();
    }

    @Override
    public String toString() {
        return value.toString();
    }
}
