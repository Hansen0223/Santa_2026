// Compare two arithmetic instruction mixes while retaining the shortest legal tape.
// Wang Jakie's arithmetic search and local extensions are credited in generative/wang/NOTICE.md.
#define main original_diverse_main
#include "../../generative/wang/anneal_diverse.cpp"
#undef main

struct MixPuzzle : Puzzle {
    struct Lineage {
        Graph graph;
        int merit;
        size_t length;
    };

    int merit(const Tape& tape, int direction) const {
        int nonlinear = 0;
        for (const auto& ins : tape) nonlinear += (ins.op == '*') + 2 * (ins.op == '/');
        return 2 * int(tape.size()) + direction * nonlinear;
    }

    Tape improve(const std::vector<Tape>& tapes) {
        const bool weighted = max_neighbors != 0;
        Tape best = tapes.front();
        Graph champion = graph_from(best);
        Lineage lanes[2] = {{champion, merit(best, weighted ? -1 : 0), best.size()},
                            {champion, merit(best, weighted ? 1 : 0), best.size()}};
        std::vector<Graph> sources;
        for (size_t k = 1; k < tapes.size() && k <= 3; ++k) sources.push_back(graph_from(tapes[k]));
        for (int iteration = 0; iteration < rounds; ++iteration) {
            const int side = (iteration / 4) % 2;
            const int direction = weighted ? (side ? 1 : -1) : 0;
            Lineage& lane = lanes[side];
            if (lane.length > best.size() + 4 || iteration % 96 == 0)
                lane = {champion, merit(best, direction), best.size()};
            Graph trial = iteration % 13 == 0 ? champion : lane.graph;
            if (!sources.empty() && iteration % 29 == 17)
                trial = sources[rng() % sources.size()];
            std::shuffle(targets.begin(), targets.end(), rng);
            size_t cap = best.size() + (iteration % 4 == 3 ? 1 : 4);
            perturb(trial, cap, 3 + rng() % 8);
            rotate(trial, cap);
            Tape current;
            if (!compile(trial, current) || current.size() > cap) continue;
            knockout(trial, current);
            if (current.size() < best.size()) {
                champion = trial;
                best = current;
            }
            int value = merit(current, direction);
            if (value < lane.merit || (value == lane.merit && rng() % 2 == 0))
                lane = {trial, value, current.size()};
            if (iteration % 16 == 15) {
                std::vector<Graph> bank = sources;
                bank.push_back(lanes[0].graph);
                bank.push_back(lanes[1].graph);
                Graph better;
                if (crossover(champion, bank, better, best)) champion = std::move(better);
            }
        }
        return best;
    }
};

#define Puzzle MixPuzzle
#include "../../generative/wang/main.inc"
#undef Puzzle
