// Minimize the temporary values required to synthesize a joint set of boundary values.
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <numeric>
#include <random>
#include <unordered_map>
#include <vector>
using Number=std::int64_t;
struct Recipe { char op; int a,b; };
struct ClosureSearch {
    Number cap;
    int seeds,goals,old,count,rounds;
    std::mt19937 rng;
    std::vector<Number> values;
    std::unordered_map<Number,int> index;
    std::vector<std::vector<Recipe>> recipes;
    std::vector<int> targets,all_helpers,best;
    using Set=std::vector<int>;

    void add(int a,int b,Number value,char op) {
        const auto pos=index.find(value);
        if(pos!=index.end() && pos->second>=seeds && pos->second!=a && pos->second!=b)
            recipes[pos->second].push_back({op,a,b});
    }
    void prepare() {
        for(int i=0;i<count;++i) index.emplace(values[i],i);
        recipes.resize(count);
        for(int a=0;a<count;++a) for(int b=0;b<=a;++b) {
            const Number x=values[a],y=values[b];
            if(x<=cap-y) add(a,b,x+y,'+');
            if(x<=cap/y) add(a,b,x*y,'*');
            int hi=x>=y?a:b,lo=x>=y?b:a;
            if(values[hi]>values[lo]) add(hi,lo,values[hi]-values[lo],'-');
            if(values[hi]%values[lo]==0) add(hi,lo,values[hi]/values[lo],'/');
        }
        for(int i=seeds;i<seeds+goals;++i) targets.push_back(i);
        for(int i=seeds+goals;i<count;++i) all_helpers.push_back(i);
    }
    bool close(const Set &allowed, std::vector<Recipe>* answer=nullptr, Set* retained=nullptr) {
        std::vector<unsigned char> known(count,0);
        std::fill_n(known.begin(),seeds,1);
        std::vector<Recipe> witness(count);
        Set order;
        int left=goals;
        auto acquire=[&](int v) {
            if(known[v]) return false;
            for(const auto &r:recipes[v]) if(known[r.a] && known[r.b]) {
                known[v]=1;witness[v]=r;order.push_back(v);
                if(v<seeds+goals) --left;
                return true;
            }
            return false;
        };
        while(left) {
            bool changed=false;
            for(int t:targets) changed|=acquire(t);
            if(!left) break;
            for(int h:allowed) changed|=acquire(h);
            if(!changed) return false;
        }
        if(!answer && !retained) return true;
        std::vector<unsigned char> live(count,0);
        for(int t:targets) live[t]=1;
        for(auto it=order.rbegin();it!=order.rend();++it) if(live[*it]) {
            Recipe r=witness[*it];live[r.a]=live[r.b]=1;
        }
        if(retained) {
            retained->clear();
            for(int h:allowed) if(live[h]) retained->push_back(h);
        }
        if(answer) {
            answer->assign(count,{0,0,0});
            for(int v:order) if(live[v]) (*answer)[v]=witness[v];
        }
        return true;
    }
    int pick(int n) { return std::uniform_int_distribution<int>(0,n-1)(rng); }
    void unique(Set &s) {
        std::sort(s.begin(),s.end());s.erase(std::unique(s.begin(),s.end()),s.end());
    }
    void minimize(Set &s) {
        std::shuffle(s.begin(),s.end(),rng);
        Set useful;
        if(!close(s,nullptr,&useful)) return;
        s=useful;
        for(int j=int(s.size())-1;j>=0;--j) {
            Set trial=s;trial.erase(trial.begin()+j);
            if(close(trial)) s.swap(trial);
        }
        unique(s);
    }
    void expand(Set &s,int v,int depth) {
        if(v>=seeds+goals) s.push_back(v);
        if(!depth || v<seeds || recipes[v].empty()) return;
        const auto r=recipes[v][pick(int(recipes[v].size()))];
        for(int u:{r.a,r.b}) if(u>=seeds+goals) expand(s,u,depth-1);
    }
    bool search() {
        best.assign(all_helpers.begin(),all_helpers.begin()+old);
        if(!close(best)) return false;
        minimize(best);
        std::vector<Set> population{best};
        for(int iter=0;iter<rounds && !best.empty();++iter) {
            Set s=(iter%5==0)?best:population[pick(int(population.size()))];
            if(iter%23==0) s=all_helpers;
            else {
                const int mutations=2+pick(9);
                for(int k=0;k<mutations;++k) {
                    if(k%2==0) expand(s,targets[pick(goals)],1+pick(3));
                    else if(!all_helpers.empty()) expand(s,all_helpers[pick(int(all_helpers.size()))],pick(3));
                }
            }
            unique(s);
            if(iter%4==0) for(auto &menu:recipes) std::shuffle(menu.begin(),menu.end(),rng);
            minimize(s);
            if(s.size()<best.size()) best=s;
            if(s.size()<=best.size()+2 && std::find(population.begin(),population.end(),s)==population.end()) {
                if(population.size()<12) population.push_back(s);else population[pick(12)]=s;
            }
        }
        return true;
    }
    void emit() {
        std::vector<Recipe> witness;
        close(best,&witness);
        int n=0;for(const auto &r:witness)n+=r.op!=0;
        std::cout<<n<<" "<<old<<" "<<best.size()<<"\n";
        for(int v=0;v<count;++v) if(witness[v].op) {
            const auto r=witness[v];std::cout<<values[v]<<" "<<r.op<<" "<<values[r.a]<<" "<<values[r.b]<<"\n";
        }
    }
};
int main() {
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    ClosureSearch s; int extra;unsigned seed;
    if(!(std::cin>>s.cap>>s.seeds>>s.goals>>s.old>>extra>>s.rounds>>seed))return 1;
    s.rng.seed(seed);s.count=s.seeds+s.goals+s.old+extra;
    if(!s.goals || s.count>500 || !s.seeds)return 2;
    s.values.resize(s.count);
    for(auto &v:s.values) if(!(std::cin>>v) || v<=0 || v>s.cap)return 2;
    s.prepare();if(int(s.index.size())!=s.count || !s.search())return 3;
    s.emit();
}