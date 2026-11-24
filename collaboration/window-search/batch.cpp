#define main prior_frontier_main
#include "sparse_core.inc"
#undef main
#include "../../proofs/local/work/gpu/sparse_reachable.hpp"
#include "../../proofs/local/work/gpu/closest-36729/sparse_star.hpp"

int main(int argc, char** argv) {
    const bool exclude = argc==2 && std::string(argv[1])=="--exclude";
    if (argc!=1 && !exclude) return 2;
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    size_t index; Num limit; unsigned n,m,h; unsigned long long cap;
    while(std::cin >> index >> limit >> n >> m >> h >> cap) {
        if (limit < 1 || limit > 1000000000000000000LL || !n || m>64 || h>3) return 2;
        SparseStar solver;
        solver.limit=limit;
        solver.inverse_terminal=true;
        solver.pair_bound=true;
        solver.early_pair=true;
        solver.enable_star=h==3;
        solver.max_nodes=cap;
        solver.seeds.resize(n);
        solver.goals.resize(m);
        for (auto &v:solver.seeds) if (!(std::cin>>v) || v<1 || v>limit) return 2;
        for (auto &v:solver.goals) if (!(std::cin>>v) || v<1 || v>limit) return 2;
        if (exclude) {
            Num forbidden;
            if (!(std::cin>>forbidden) || forbidden<1 || forbidden>limit ||
                std::find(solver.seeds.begin(),solver.seeds.end(),forbidden)!=solver.seeds.end() ||
                std::find(solver.goals.begin(),solver.goals.end(),forbidden)!=solver.goals.end()) return 2;
            solver.bans.insert(forbidden);
        }
        std::sort(solver.goals.begin(),solver.goals.end());
        solver.goals.erase(std::unique(solver.goals.begin(),solver.goals.end()),solver.goals.end());
        solver.prepare();
        if(solver.enable_star)solver.prepare_stars();
        bool found=solver.run_frontier(h);
        std::cout<<index<<' '<<(found?"FOUND":solver.interrupted?"UNKNOWN":"UNSAT")<<' '<<solver.nodes<<' '<<solver.last_candidates;
        if(found)for(auto value:solver.witness)std::cout<<' '<<value;
        std::cout<<'\n'<<std::flush;
    }
}
