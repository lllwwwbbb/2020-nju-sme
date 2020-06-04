package se;

import se.analysis.ControlDependAnalysis;
import se.analysis.DominanceAnalysis;
import se.analysis.DataDependAnalysis;
import se.analysis.sourcemap.JStmt;
import soot.*;
import soot.options.Options;
import soot.toolkits.scalar.Pair;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.*;
import java.util.stream.Collectors;


public class Main {

    private static Map<String, String> optMap = new HashMap<>();
    private static final String OPT_FEATURES_LIST = "--features-list";
    private static String baseName;

    private static String[] parseArgs(String[] args) {
        List<String> remList = new ArrayList<>();
        for (int i = 0; i < args.length; i ++) {
            if (args[i].equals(OPT_FEATURES_LIST)) {
                if (i < args.length - 1)
                    optMap.put(args[i], args[i + 1]);
                else
                    throw new IllegalArgumentException(OPT_FEATURES_LIST + " followed by no option");
                i += 1;
            } else {
                remList.add(args[i]);
            }
        }
        if (optMap.containsKey(OPT_FEATURES_LIST))
            baseName = Paths.get(optMap.get(OPT_FEATURES_LIST)).getFileName().toString().split("\\.", 2)[0];
        else
            throw new IllegalArgumentException(OPT_FEATURES_LIST + " should be provided");
        return remList.toArray(new String[0]);
    }

    private static Map<String, Set<Integer>> clzLinenoSet = new HashMap<>();

    private static void parseFeaturesList(String featuresListPath) {
        try {
            List<String> featuresList = Files.readAllLines(Paths.get(featuresListPath));
            for (int i = 1; i < featuresList.size(); i ++) {
                String[] stmt = featuresList.get(i).split(",", 2)[0].split("#");
                clzLinenoSet.putIfAbsent(stmt[0], new HashSet<>());
                clzLinenoSet.get(stmt[0]).add(Integer.valueOf(stmt[1]));
            }
        } catch (IOException e) {
            e.printStackTrace();
            System.exit(-1);
        }
    }

    public static void main(String[] args) {
        long startMillis = System.currentTimeMillis();
        // -cp [soot-class-path] --features-list [features-list] -d [output-dir]
        String[] remArgs = parseArgs(args);
        parseFeaturesList(optMap.get(OPT_FEATURES_LIST));

        Options opt = Options.v();
        opt.classes().addAll(clzLinenoSet.keySet());
        opt.parse(remArgs);
        opt.set_prepend_classpath(true);
        opt.set_src_prec(Options.src_prec_only_class);
        opt.set_keep_line_number(true);
        opt.set_omit_excepting_unit_edges(true);
        opt.setPhaseOption("jb", "use-original-names:true");

        opt.set_allow_phantom_refs(true);
        opt.set_no_bodies_for_excluded(true);
//        opt.set_whole_program(true);
//        opt.set_main_class("Test");

        Scene scene = Scene.v();
        scene.loadNecessaryClasses();
        Set<Pair<JStmt, JStmt>> ddSet = new HashSet<>(), dmSet = new HashSet<>(), cdSet = new HashSet<>();
        Set<Pair<String, String>> stmtMethodPairs = new HashSet<>();
        for (SootClass sc: scene.getApplicationClasses()) {
            Set<Integer> linenoSet = clzLinenoSet.get(sc.getName());
            if (opt.verbose())
                System.out.println("Start process class: " + sc.getName());
            if (sc.getMethods().size() == 0) {
                System.err.println("No method found in class :" + sc.getName());
                System.exit(-1);
            }
            for (SootMethod sm : sc.getMethods()) {
                if (linenoSet.isEmpty())
                    break;
                if (!sm.isConcrete())
                    continue;
                Body body = sm.retrieveActiveBody();
                int oldSize = linenoSet.size();
                Set<Integer> mLineSet = getLineSet(body);
                for (Integer lineno: mLineSet) {
                    if (linenoSet.contains(lineno))
                        stmtMethodPairs.add(new Pair<>(sc.getName() + '#' + lineno, sm.getSignature()));
                }
//                linenoSet.removeIf(mLineSet::contains);
//                if (linenoSet.size() > oldSize - 2)
//                    continue;
//                ddSet.addAll(new DataDependAnalysis(body).getJStmtRelationSet());
//                cdSet.addAll(new ControlDependAnalysis(body).getJStmtRelationSet());
            }
            if (opt.verbose())
                System.out.println("Done process class: " + sc.getName());
        }
        try {
//            Files.write(Paths.get(opt.output_dir(), baseName + ".ddg"),
//                    ddSet.stream().map(p -> String.format("%s,%s", p.getO1(), p.getO2())).collect(Collectors.toList()),
//                    StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
//            Files.write(Paths.get(opt.output_dir(), baseName + ".cdg"),
//                    cdSet.stream().map(p -> String.format("%s,%s", p.getO1(), p.getO2())).collect(Collectors.toList()),
//                    StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
            Files.write(Paths.get(opt.output_dir(), baseName + ".mmap"),
                    stmtMethodPairs.stream().map(p -> String.format("%s,%s", p.getO1(), p.getO2())).collect(Collectors.toList()),
                    StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
        } catch (IOException e) {
            e.printStackTrace();
            System.exit(-1);
        }
//        opt.setPhaseOption("cg", "implicit-entry:false");
//        opt.setPhaseOption("cg.cha", "apponly:true");
//        PackManager.v().getPack("cg").apply();
//        CallGraph callGraph = scene.getCallGraph();
        long endMillis = System.currentTimeMillis();
        System.out.println("cost time : " + (endMillis - startMillis)/1000. + " s");
    }

    private static Pair<Integer, Integer> getLineRange(Body body) {
        int min = Integer.MAX_VALUE, max = -1;
        for (Unit u: body.getUnits()) {
            int lineno = u.getJavaSourceStartLineNumber();
            if (lineno < 0)
                continue;
            if (lineno < min)
                min = lineno;
            if (lineno > max)
                max = lineno;
        }
        return new Pair<>(min, max);
    }

    private static Set<Integer> getLineSet(Body body) {
        Set<Integer> lineSet = body.getUnits().stream()
                .map(Unit::getJavaSourceStartLineNumber).filter(i -> i >= 0).collect(Collectors.toSet());
        int max = lineSet.stream().max(Integer::compareTo).get();
        int min = lineSet.stream().min(Integer::compareTo).get();
        for (int i = min; i <= max; i ++) {
            lineSet.add(i);
        }
        return lineSet;
    }
}
