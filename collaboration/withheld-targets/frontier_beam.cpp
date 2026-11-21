// Branch over several complete partial programs with different target orders and intermediate values.
#define SANTA_VIRTUAL_LIBRARY
#include "../../solvers/native/virtual.cpp"

struct Partial {
    Puzzle p;
    double estimate;
};
struct Choice {
    Plan steps;
    Int goal;
};
static vector<Partial> advance(const Puzzle& parent,const Trace& fallback,int width,int leaves,int salt) {
    vector<Int> pending;
    for(Int t:parent.targets) if(!parent.defs.count(t)) pending.push_back(t);
    vector<Int> available;
    set<Int> present;
    auto add=[&](Int v){if(present.insert(v).second && int(available.size())<leaves)available.push_back(v);};
    for(auto it=parent.order.rbegin();it!=parent.order.rend() && available.size()<18;++it)add(*it);
    // The caller ranks retained values by how often the removed branches need them.
    for(Int v:parent.starts)add(v);
    LiveBank bank(parent.limit,125000);
    bank.extend(available);
    vector<Choice> options;
    map<Int,int> price;
    map<Int,vector<Plan>> routes;
    for(Int t:pending) {
        Plan old=trace_plan(t,fallback,parent);
        int bound=min(27,int(old.size())+4);
        TargetSearch walk(bank,2,bound,.21,4);
        vector<Plan> found{old};
        Plan first=walk.run(t,8);
        if(!first.empty())found.push_back(move(first));
        for(auto [cost,node,id]:walk.finishes) {
            if(node!=walk.best_node)found.push_back(walk.reconstruct(t,node,id));
        }
        set<vector<Int>> seen;
        price[t]=int(old.size());
        for(auto &item:found){
            Plan plan=incremental(move(item),parent);
            if(plan.empty())continue;
            vector<Int> signature;
            for(auto e:plan)signature.push_back(e.out);
            sort(signature.begin(),signature.end());
            if(!seen.insert(signature).second)continue;
            price[t]=min(price[t],int(plan.size()));routes[t].push_back(plan);
            options.push_back({move(plan),t});
        }
    }
    vector<Partial> children;
    for(const auto &c:options) {
        Puzzle p=parent;commit(p,c.steps);
        double remaining=0;
        for(Int t:pending) if(!p.defs.count(t)){
            int next=price[t];
            for(auto &plan:routes[t]) {
                int n=0;for(auto e:plan)n+=!p.defs.count(e.out);
                next=min(next,n);
            }
            for(auto e:c.steps)next=min(next,immediate(t,e.out,bank));
            remaining+=next;
        }
        // Partial cost and estimated work on every unfinished target are measured in operations.
        double score=p.order.size()+.93*remaining;
        std::uint64_t hash=std::uint64_t(salt);
        for(auto e:c.steps)hash=hash*0x9e3779b97f4a7c15ULL+std::uint64_t(e.out);
        score+=.03*double(hash&1023)/1024.;
        children.push_back({move(p),score});
    }
    stable_sort(children.begin(),children.end(),[](const Partial&a,const Partial&b){return a.estimate<b.estimate;});
    if(int(children.size())>width*2)children.erase(children.begin()+width*2,children.end());
    return children;
}

int main(int argc,char**argv) {
    if(argc!=4)return 2;
    const int width=stoi(argv[1]), leaves=stoi(argv[2]), salt=stoi(argv[3]);
    if(width<1 || leaves<2)return 2;
    TARGET_LEAVES=true;join_mode=13;
    Int cap;int ns,nt,ne;
    if(!(cin>>cap>>ns>>nt>>ne))return 1;
    Puzzle seed(cap,2);seed.starts.resize(ns);seed.targets.resize(nt);
    for(auto &v:seed.starts){cin>>v;seed.defs[v]={v};}
    for(auto &v:seed.targets)cin>>v;
    Trace trace;
    for(int j=0;j<ne;++j){Edge e;cin>>e.out>>e.op>>e.a>>e.b;trace.emplace(e.out,e);}
    Puzzle best=seed;
    for(Int t:seed.targets)commit(best,trace_plan(t,trace,best));
    vector<Partial> states{{seed,0.}};
    int expanded=0;
    for(int depth=0;depth<nt && !states.empty();++depth) {
        vector<Partial> next;
        for(const auto &s:states) {
            auto children=advance(s.p,trace,width,leaves,salt+depth);++expanded;
            for(auto &child:children){
                int missing=0;for(Int t:seed.targets)missing+=!child.p.defs.count(t);
                if(!missing){if(child.p.order.size()<best.order.size())best=move(child.p);continue;}
                if(child.p.order.size()+missing>=best.order.size())continue;
                next.push_back(move(child));
            }
        }
        stable_sort(next.begin(),next.end(),[](const Partial&a,const Partial&b){return a.estimate<b.estimate;});
        set<vector<Int>> chosen;states.clear();
        for(auto &s:next) {
            vector<Int> signature=s.p.order;sort(signature.begin(),signature.end());
            if(chosen.insert(signature).second)states.push_back(move(s));
            if(int(states.size())>=width)break;
        }
    }
    cout<<best.order.size()<<" "<<expanded<<"\n";
    for(Int v:best.order){auto [a,b]=best.args.at(v);cout<<v<<" "<<best.defs.at(v).op<<" "<<a<<" "<<b<<"\n";}
}