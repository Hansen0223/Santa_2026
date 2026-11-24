#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using Value = std::int64_t;
using Values = std::vector<Value>;
using Mask = std::uint64_t;

static Mask mix(Mask n) {
    n += 0x9e3779b97f4a7c15ULL;
    n = (n ^ (n >> 30)) * 0xbf58476d1ce4e5b9ULL;
    n = (n ^ (n >> 27)) * 0x94d049bb133111ebULL;
    return n ^ (n >> 31);
}

struct State {
    Values values;
    Mask reached = 0, key = 0;
    double rank = 0;
};

struct Search {
    Value limit;
    int width, branch, profile, budget;
    unsigned salt;
    Values goals, prefix;
    std::unordered_map<Value,Mask> target;
    std::unordered_set<Value> incumbent, known;
    Mask all;
    long long expanded = 0, transitions = 0;

    template<class F>
    void operations(Value a, Value b, F result) const {
        if (a < b) std::swap(a, b);
        if (a <= limit - b) result(a + b);
        if (a != b) result(a - b);
        if (a <= limit / b) result(a * b);
        if (a % b == 0) result(a / b);
    }

    template<class F>
    void inverse(Value t, Value a, F add) const {
        if (t != a) add(std::abs(t - a));
        if (t <= limit - a) add(t + a);
        if (t <= limit / a) add(t * a);
        if (t % a == 0) add(t / a);
        if (a % t == 0) add(a / t);
    }

    Mask target_bit(Value v) const {
        auto found = target.find(v);
        return found == target.end() ? 0 : found->second;
    }

    void insert(State& state, Value value) {
        if (!known.insert(value).second) return;
        state.values.push_back(value);
        state.reached |= target_bit(value);
        state.key ^= mix(value);
    }

    void saturate(State& state, int first) {
        for (int i = first; i < static_cast<int>(state.values.size()); ++i) {
            Value a = state.values[i];
            for (int j = 0; j <= i; ++j)
                operations(a, state.values[j], [&](Value v) {
                    if (target_bit(v)) insert(state, v);
                });
        }
    }

    State closure(State state, Value next) {
        known.clear();
        known.insert(state.values.begin(), state.values.end());
        int first = static_cast<int>(state.values.size());
        insert(state, next);
        saturate(state, first);
        return state;
    }

    std::vector<State> children(const State& state, int depth) {
        ++expanded;
        known.clear();
        known.insert(state.values.begin(), state.values.end());
        std::unordered_map<Value,Mask> demand;
        auto request = [&](Value v, Mask bit) {
            if (!known.count(v)) demand[v] |= bit;
        };
        for (Value t : goals) {
            Mask bit = target.at(t);
            if (bit & state.reached) continue;
            for (Value a : state.values)
                inverse(t, a, [&](Value v) { request(v, bit); });
            if (t % 2 == 0) request(t / 2, bit);
            Value square = static_cast<Value>(std::sqrt(static_cast<long double>(t)));
            if (square * square == t) request(square, bit);
        }
        struct Choice { Value value; double rank; };
        std::vector<Choice> options;
        std::unordered_set<Value> offered;
        for (int i = 0; i < static_cast<int>(state.values.size()); ++i) {
            for (int j = 0; j <= i; ++j) {
                operations(state.values[i], state.values[j], [&](Value v) {
                    if (known.count(v) || !offered.insert(v).second) return;
                    ++transitions;
                    Mask immediate = 0, bridge = 0;
                    auto exact = demand.find(v);
                    if (exact != demand.end()) immediate = exact->second;
                    if (profile != 0) {
                        auto lookup = [&](Value w) {
                            auto hit = demand.find(w);
                            if (hit != demand.end()) bridge |= hit->second;
                        };
                        for (Value a : state.values) operations(v, a, lookup);
                        operations(v, v, lookup);
                    }
                    double noise = static_cast<double>(mix(state.key ^ mix(v) ^ salt) & 65535) / 65536;
                    double priority = 5.0 * __builtin_popcountll(immediate)
                                      + 0.85 * __builtin_popcountll(bridge & ~immediate)
                                      + (profile == 2 ? 2.4 : .9) * incumbent.count(v)
                                      + (profile == 3 ? 3.2 : 1.3) * noise;
                    if (v < 128 && depth < 5) priority += .2;
                    options.push_back({v, priority});
                });
            }
        }
        int retained = std::min(branch, static_cast<int>(options.size()));
        std::partial_sort(options.begin(), options.begin() + retained, options.end(),
                          [](const Choice& a, const Choice& b) {
                              if (a.rank != b.rank) return a.rank > b.rank;
                              return a.value < b.value;
                          });
        std::vector<State> output;
        for (int i = 0; i < retained; ++i) {
            State next = closure(state, options[i].value);
            next.rank = __builtin_popcountll(next.reached) * 6.0 + options[i].rank
                        + .22 * state.rank;
            output.push_back(std::move(next));
        }
        return output;
    }

    State run() {
        State initial;
        known.clear();
        for (Value v : prefix) insert(initial, v);
        saturate(initial, 0);
        std::vector<State> beam{std::move(initial)};
        for (int depth = 0; depth <= budget && !beam.empty(); ++depth) {
            for (const State& s : beam)
                if (s.reached == all) return s;
            if (depth == budget) break;
            std::unordered_map<Mask,State> next;
            for (const State& s : beam) {
                for (State candidate : children(s, depth)) {
                    auto old = next.find(candidate.key);
                    if (old == next.end() || old->second.rank < candidate.rank)
                        next.insert_or_assign(candidate.key, std::move(candidate));
                }
            }
            beam.clear();
            for (auto& entry : next) beam.push_back(std::move(entry.second));
            int retained = std::min(width, static_cast<int>(beam.size()));
            std::partial_sort(beam.begin(), beam.begin() + retained, beam.end(), [](const State& a, const State& b) {
                if (a.rank != b.rank) return a.rank > b.rank;
                return a.key < b.key;
            });
            beam.resize(retained);
        }
        return {};
    }
};

int main() {
    Search s;
    int seeds, size, targets, hints;
    if (!(std::cin >> s.limit >> seeds >> size >> targets >> hints >>
          s.budget >> s.width >> s.branch >> s.profile >> s.salt)) return 1;
    if (s.limit < 1 || s.limit > 1000000000000000000LL || seeds < 1 || size < seeds || targets < 1 ||
        targets > 60 || s.budget < 0 || s.width < 1 || s.branch < 1) return 2;
    s.goals.resize(targets);
    s.prefix.resize(size);
    for (Value& v : s.prefix) {
        if (!(std::cin >> v) || v < 1 || v > s.limit) return 2;
    }
    for (int i = 0; i < targets; ++i) {
        Value& t = s.goals[i];
        if (!(std::cin >> t) || t < 1 || t > s.limit || s.target.count(t)) return 2;
        s.target[t] = Mask(1) << i;
    }
    for (int i = 0; i < hints; ++i) {
        Value v;
        if (!(std::cin >> v) || v < 1 || v > s.limit) return 2;
        s.incumbent.insert(v);
    }
    s.all = (Mask(1) << targets) - 1;
    State result = s.run();
    std::cout << (result.reached == s.all) << ' ' << s.expanded << ' ' << s.transitions;
    if (result.reached == s.all)
        for (Value value : result.values) std::cout << ' ' << value;
    std::cout << '\n';
}
