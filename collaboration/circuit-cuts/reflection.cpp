// Search a value graph and its reflection about a common arithmetic center.
// Uses Wang Jakie's graph selection and register allocator, see generative/wang/NOTICE.md.
#include "../../generative/wang/common.inc"
#include "../../generative/wang/compact.inc"
#include "../../generative/wang/cross.inc"

    Tape improve(const std::vector<Tape>& tapes) {
        Tape best = tapes.front();
        Graph base = graph_from(best);
        std::vector<Value> values;
        for (const auto& entry : base) values.push_back(entry.first);
        std::sort(values.begin(), values.end());
        std::unordered_set<Value> actual(values.begin(), values.end());
        std::unordered_set<Value> goals(targets.begin(), targets.end());
        std::map<Value, int> support;
        // Exact sums already witnessed in the parent favor occupied reflection centers.
        for (size_t i = 0; i < values.size(); ++i) {
            for (size_t j = 0; j <= i; ++j) {
                Value a = values[i], b = values[j];
                if (a < 64 || a > limit - b) continue;
                Value center = a + b;
                if (center < 256) continue;
                support[center] += 1 + 4 * (goals.count(a) + goals.count(b));
            }
        }
        std::vector<std::pair<int,Value>> ranked;
        for (auto [center, weight] : support) {
            if (weight >= 4) ranked.emplace_back(-(weight + 4 * int(actual.count(center))), center);
        }
        std::sort(ranked.begin(), ranked.end());
        int tested = 0;
        for (auto [ignored, center] : ranked) {
            if (tested >= rounds) break;
            std::vector<Value> extras;
            if (!actual.count(center)) extras.push_back(center);
            for (Value v : values) {
                if (v < center && !actual.count(center - v)) extras.push_back(center - v);
            }
            if (extras.size() < 2) continue;
            ++tested;
            if (!max_neighbors) extras.clear();
            Graph winning;
            if (crossover(base, {}, winning, best, extras)) base = std::move(winning);
        }
        return best;
    }
};
#include "../../generative/wang/main.inc"
