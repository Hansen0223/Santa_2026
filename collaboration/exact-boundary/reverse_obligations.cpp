// Regress sets of outstanding values through inverse arithmetic recipes. Prefixes are supplied
// row by row. Search states are arithmetic obligations, not forward permutations of helpers.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <unordered_map>
#include <unordered_set>
#include <vector>
using V=std::vector<int>;
using H=uint64_t;
H mix(H x){x+=0x9e3779b97f4a7c15ULL;x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;x=(x^(x>>27))*0x94d049bb133111ebULL;return x^(x>>31);}
struct Pair{int a,b; double score;};
struct Node{V missing; int parent, out; double rank;};
struct Backward{
    int cap, width, variant, bound, original_seeds;
    unsigned salt;
    V start, goals, incumbent, donor, anchors;
    std::vector<unsigned char> cost,is_start,is_donor,is_goal;
    std::vector<V> levels;
    std::unordered_map<int,std::vector<Pair>> recipe_cache;
    std::vector<Node> history; V witness;
    long long expanded=0,transitions=0,duplicates=0,frontiers=0;
    template<class F>void ops(int a,int b,F f){
        if(a<=cap-b)f(a+b);if(a<=cap/b)f(a*b);if(a<b)std::swap(a,b);
        if(a>b)f(a-b);if(a%b==0)f(a/b);
    }
    template<class F>void inverse(int t,int a,F f){
        auto give=[&](int b){if(b>0&&b<=cap&&b!=t&&a!=t)f(a,b);};
        if(t>a)give(t-a);if(a>t)give(a-t);if(t<=cap-a)give(t+a);
        if(t<=cap/a)give(t*a);if(t%a==0)give(t/a);if(a%t==0)give(a/t);
    }
    void prepare(){
        cost.assign(cap+1,10);is_start.assign(cap+1,0);is_donor=is_start;is_goal=is_start;
        for(int v:incumbent)is_donor[v]=1;
        for(int v:goals)is_goal[v]=1;
        levels.resize(8);
        for(int x:start)if(!is_start[x]){is_start[x]=1;cost[x]=0;levels[0].push_back(x);}
        for(int n=1;n<=7;n++){
            for(int i=0;i*2<=n-1;i++){
                int j=n-1-i;
                for(size_t ai=0;ai<levels[i].size();ai++){
                    int a=levels[i][ai];size_t upto=i==j?ai+1:levels[j].size();
                    for(size_t bi=0;bi<upto;bi++)ops(a,levels[j][bi],[&](int z){
                        if(cost[z]>n){cost[z]=n;levels[n].push_back(z);}
                    });
                }
            }
            if(levels[n].empty())break;
        }
        anchors=start;anchors.insert(anchors.end(),goals.begin(),goals.end());
        anchors.insert(anchors.end(),incumbent.begin(),incumbent.end());
        for(int z=1;z<=96;z++)anchors.push_back(z);
        for(int j=1;j<=2;j++){
            V layer=levels[j];
            if(layer.size()>160){std::sort(layer.begin(),layer.end(),[&](int a,int b){return mix(salt^a)<mix(salt^b);});layer.resize(160);}
            anchors.insert(anchors.end(),layer.begin(),layer.end());
        }
        std::sort(anchors.begin(),anchors.end());anchors.erase(std::unique(anchors.begin(),anchors.end()),anchors.end());
    }
    double atom(int v)const{
        return cost[v]+(variant&1?-.45*is_donor[v]:0)-.30*is_goal[v];
    }
    const std::vector<Pair>& recipes(int t){
        auto [it,new_entry]=recipe_cache.try_emplace(t);
        if(!new_entry)return it->second;
        auto& choices=it->second;std::unordered_set<H> seen;
        auto add=[&](int a,int b){
            if(a==t||b==t)return;if(a>b)std::swap(a,b);H key=(H(a)<<32)|unsigned(b);
            if(!seen.insert(key).second)return;
            double ra=atom(a),rb=a==b?0:atom(b);
            double score=std::max(ra,rb)*.77+(ra+rb)*.86
                   -(a==b?.19:0)+double(mix(key^salt)&65535)/65536.*.17;
            choices.push_back({a,b,score});
        };
        for(int a:anchors)inverse(t,a,add);
        for(int a=2;a<=t/a;a++)if(t%a==0)add(a,t/a);
        if((t&1)==0)add(t/2,t/2);
        int root=int(std::sqrt(t));if(root*root==t)add(root,root);
        size_t keep=std::min(choices.size(),size_t(variant&2?34:20));
        std::partial_sort(choices.begin(),choices.begin()+keep,choices.end(),[](auto&x,auto&y){return x.score<y.score;});choices.resize(keep);
        return choices;
    }
    H fingerprint(const V& q)const{H h=0;for(int v:q)h^=mix(v);return h;}
    double rank(const V& q,int level,H h)const{
        double sum=0,mx=0;int expensive=0,built=0;
        for(int v:q){double c=atom(v);sum+=c;mx=std::max(mx,c);expensive+=cost[v]>=4;built+=cost[v]<=1;}
        double noise=double(mix(h^(H(level)<<32)^salt)&65535)/65536.;
        return (variant&4?1.42:2.1)*q.size()+sum*(variant&4?.82:.55)+mx*.55+expensive*.14-built*.05
               +noise*(variant&8?2.05:.62);
    }
    bool run(){
        prepare();V initial;for(int v:goals)if(!is_start[v])initial.push_back(v);std::sort(initial.begin(),initial.end());
        history.push_back({initial,-1,0,0});V beam{0};
        int budget=bound-(int(start.size())-original_seeds);if(budget<int(initial.size()))return false;
        for(int d=1;d<=budget&&!beam.empty();d++){
            std::vector<Node> next;std::unordered_set<H> seen;frontiers+=beam.size();
            for(int idx:beam){
                const V& q=history[idx].missing;expanded++;H hash=fingerprint(q);
                V order=q;std::sort(order.begin(),order.end(),[&](int a,int b){
                    return cost[a]+(double(mix(hash^a^salt)&255)/256.) > cost[b]+(double(mix(hash^b^salt)&255)/256.);
                });
                for(int oi=0;oi<int(order.size());oi++){
                    int t=order[oi];V base=q;base.erase(std::lower_bound(base.begin(),base.end(),t));H base_hash=hash^mix(t);
                    bool success=false;
                    auto try_pair=[&](int a,int b,bool dynamic){
                        if(success)return;
                        bool add_a=!is_start[a]&&!std::binary_search(base.begin(),base.end(),a);
                        bool add_b=b!=a&&!is_start[b]&&!std::binary_search(base.begin(),base.end(),b);
                        if(oi>=3&&!dynamic&&(add_a||add_b))return;
                        if(oi>=3&&dynamic&&add_a&&add_b)return;
                        if(d+int(base.size())+int(add_a)+int(add_b)>budget)return;
                        H h=base_hash^(add_a?mix(a):0)^(add_b?mix(b):0);transitions++;
                        if(!seen.insert(h).second){duplicates++;return;}
                        if(base.empty()&&!add_a&&!add_b){
                            witness=start;witness.push_back(t);
                            for(int p=idx;p>0;p=history[p].parent)witness.push_back(history[p].out);
                            success=true;return;
                        }
                        V z=base;if(add_a)z.push_back(a);if(add_b)z.push_back(b);std::sort(z.begin(),z.end());
                        auto r=rank(z,d,h);next.push_back({std::move(z),idx,t,r});
                    };
                    for(auto&a:recipes(t))try_pair(a.a,a.b,false);
                    for(int a:base)inverse(t,a,[&](int x,int y){try_pair(x,y,true);});
                    if(success)return true;
                }
            }
            size_t keep=std::min(next.size(),size_t(width));
            if(keep<next.size())std::nth_element(next.begin(),next.begin()+keep,next.end(),[](auto&a,auto&b){return a.rank<b.rank;});
            next.resize(keep);std::sort(next.begin(),next.end(),[](auto&a,auto&b){return a.rank<b.rank;});
            beam.clear();for(auto& n:next){beam.push_back(history.size());history.push_back(std::move(n));}
        }
        return false;
    }
};
int main(){
    int cap,base,ns,ng,nh,width,variant,bound;unsigned seed;
    while(std::cin>>cap>>base>>ns>>ng>>nh>>width>>variant>>bound>>seed){
        Backward w;w.cap=cap;w.width=width;w.variant=variant;w.bound=bound;w.original_seeds=base;w.salt=seed;
        for(int k=0;k<ns;k++){int v;std::cin>>v;w.start.push_back(v);}
        for(int k=0;k<ng;k++){int v;std::cin>>v;w.goals.push_back(v);}
        for(int k=0;k<nh;k++){int v;std::cin>>v;w.incumbent.push_back(v);}
        bool yes=w.run();
        std::cout<<yes<<' '<<w.expanded<<' '<<w.transitions<<' '<<w.duplicates<<' '<<w.recipe_cache.size();
        for(int v:w.witness)std::cout<<' '<<v;std::cout<<'\n'<<std::flush;
    }
}
