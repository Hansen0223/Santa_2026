#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using Values = std::vector<int>;
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
    int limit, width, branch, profile, budget;
    unsigned salt;
    Values goals, prefix;
    std::vector<Mask> target;
    std::vector<unsigned char> incumbent;
    std::vector<std::uint32_t> known, offered;
    std::uint32_t stamp = 0;
    Mask all;
    long long expanded = 0, transitions = 0;

    template<class F>
    void operations(int a, int b, F result) const {
        if (a < b) std::swap(a, b);
        if (a <= limit - b) result(a + b);
        if (a != b) result(a - b);
        if (a <= limit / b) result(a * b);
        if (a % b == 0) result(a / b);
    }

    template<class F>
    void inverse(int t, int a, F add) const {
        if (t != a) add(std::abs(t - a));
        if (t <= limit - a) add(t + a);
        if (t <= limit / a) add(t * a);
        if (t % a == 0) add(t / a);
        if (a % t == 0) add(a / t);
    }

    void insert(State& state, int value) {
        if (known[value] == stamp) return;
        known[value] = stamp;
        state.values.push_back(value);
        state.reached |= target[value];
        state.key ^= mix(value);
    }

    void saturate(State& state, int first) {
        for (int i = first; i < static_cast<int>(state.values.size()); ++i) {
            int a = state.values[i];
            for (int j = 0; j <= i; ++j)
                operations(a, state.values[j], [&](int v) {
                    if (target[v]) insert(state, v);
                });
        }
    }

    State closure(State state, int next) {
        ++stamp;
        for (int v : state.values) known[v] = stamp;
        int first = static_cast<int>(state.values.size());
        insert(state, next);
        saturate(state, first);
        return state;
    }

    std::vector<State> children(const State& state, int depth) {
        ++expanded;
        ++stamp;
        for (int v : state.values) known[v] = stamp;
        std::unordered_map<int,Mask> demand;
        auto request = [&](int v, Mask bit) {
            if (known[v] != stamp) demand[v] |= bit;
        };
        for (int t : goals) {
            Mask bit = target[t];
            if (bit & state.reached) continue;
            for (int a : state.values)
                inverse(t, a, [&](int v) { request(v, bit); });
            if (t % 2 == 0) request(t / 2, bit);
            int square = static_cast<int>(std::sqrt(t));
            if (square * square == t) request(square, bit);
        }
        struct Choice { int value; double rank; };
        std::vector<Choice> options;
        for (int i = 0; i < static_cast<int>(state.values.size()); ++i) {
            for (int j = 0; j <= i; ++j) {
                operations(state.values[i], state.values[j], [&](int v) {
                    if (known[v] == stamp || offered[v] == stamp) return;
                    offered[v] = stamp;
                    ++transitions;
                    Mask immediate = 0, bridge = 0;
                    auto exact = demand.find(v);
                    if (exact != demand.end()) immediate = exact->second;
                    if (profile != 0) {
                        auto lookup = [&](int w) {
                            auto hit = demand.find(w);
                            if (hit != demand.end()) bridge |= hit->second;
                        };
                        for (int a : state.values) operations(v, a, lookup);
                        operations(v, v, lookup);
                    }
                    double noise = static_cast<double>(mix(state.key ^ mix(v) ^ salt) & 65535) / 65536;
                    double priority = 5.0 * __builtin_popcountll(immediate)
                                      + 0.85 * __builtin_popcountll(bridge & ~immediate)
                                      + (profile == 2 ? 2.4 : .9) * incumbent[v]
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
        ++stamp;
        for (int v : prefix) insert(initial, v);
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
    if (s.limit < 1 || s.limit > 2000000 || seeds < 1 || size < seeds || targets < 1 ||
        targets > 60 || s.budget < 0 || s.width < 1 || s.branch < 1) return 2;
    s.target.resize(s.limit + 1);
    s.known.resize(s.limit + 1);
    s.offered.resize(s.limit + 1);
    s.incumbent.resize(s.limit + 1);
    s.goals.resize(targets);
    s.prefix.resize(size);
    for (int& v : s.prefix) {
        if (!(std::cin >> v) || v < 1 || v > s.limit) return 2;
    }
    for (int i = 0; i < targets; ++i) {
        int& t = s.goals[i];
        if (!(std::cin >> t) || t < 1 || t > s.limit || s.target[t]) return 2;
        s.target[t] = Mask(1) << i;
    }
    for (int i = 0; i < hints; ++i) {
        int v;
        if (!(std::cin >> v) || v < 1 || v > s.limit) return 2;
        s.incumbent[v] = 1;
    }
    s.all = (Mask(1) << targets) - 1;
    State result = s.run();
    std::cout << (result.reached == s.all) << ' ' << s.expanded << ' ' << s.transitions;
    if (result.reached == s.all)
        for (int value : result.values) std::cout << ' ' << value;
    std::cout << '\n';
}
