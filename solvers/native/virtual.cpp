// SPDX-License-Identifier: Apache-2.0
// Includes Tony Li/konbu17's integer index and arithmetic graph emitter.
// See generative/NOTICE.md and generative/LICENSE-APACHE-2.0.txt.
// This planner incrementally promotes reusable expressions, compares unsolved
// targets against the same dictionary, and can reconstruct a selected subproblem.
#define main vanilla_solver_main
#include "../../generative/konbu.cpp"
#undef main
#include <random>
#include <unordered_set>
#include "integer_factors.hpp"

struct Edge {
    Int out, a, b;
    char op;
};
using Plan = vector<Edge>;
static int join_mode=0;

struct LiveBank {
    const Int limit;
    const size_t max_entries;
    Index index;
    vector<Expr> nodes;
    vector<int> zero, one;
    array<vector<pair<Int,int>>,3> near, fresh;
    vector<int> moduli{16, 81, 125, 256, 1024, 4096};
    vector<vector<vector<int>>> columns;
    unordered_set<Int> missing_three;
    unordered_map<Int,uint64_t> scaffold;
    vector<uint64_t> masks;
    uint64_t paid_mask=0;
    struct Undo {int id; Expr expr; uint64_t mask;};
    vector<Undo> undo;
    size_t n_before=0, zero_before=0, one_before=0, slots_before=0;
    uint64_t paid_before=0;
    bool staged=false;
    unordered_map<Int,vector<factors::U>> divisor_cache;
    LiveBank(Int cap, size_t max_entries) : limit(cap), max_entries(max_entries), index(-16) {}

    void reset() {
        index.clear(); nodes.clear(); zero.clear(); one.clear();
        for (auto &v:near) v.clear();
        for (auto &v:fresh) v.clear();
        columns.clear();
        missing_three.clear();
        masks.clear();
    }
    void remember(Int v,int a,int b,char op,int price) {
        if(v<1 || v>limit) return;
        int id=index.get(v);
        if(id<0) {
            if(price==2 && nodes.size()>=max_entries) return;
            id=nodes.size();
            index.insert(v,id);
            nodes.push_back({v,a,b,op,price});
            if(join_mode&64) masks.push_back(0);
        } else {
            if(nodes[id].cost<=price) return;
            if(staged && size_t(id)<n_before)
                undo.push_back({id,nodes[id],(join_mode&64)?masks[id]:0});
            nodes[id]={v,a,b,op,price};
        }
        if(join_mode&64) {
            if(price) masks[id]=masks[a]|masks[b];
            else {
                auto it=scaffold.find(v);
                masks[id]=it==scaffold.end()?0:it->second;
            }
        }
        if(price==0) zero.push_back(id);
        if(price==1) one.push_back(id);
        fresh[price].emplace_back(v,id);
    }
    void join(int i,int j,int price) {
        Int a=nodes[i].v,b=nodes[j].v;
        remember(a+b,i,j,'+',price);
        if(a>b) { remember(a-b,i,j,'-',price); if(a%b==0) remember(a/b,i,j,'/',price); }
        if(b>a) { remember(b-a,j,i,'-',price); if(b%a==0) remember(b/a,j,i,'/',price); }
        if(a<=limit/b) remember(a*b,i,j,'*',price);
    }
    void extend(const vector<Int>& values) {
        missing_three.clear();
        size_t first=zero.size(), old1=one.size();
        for(Int v:values) remember(v,-1,-1,0,0);
        for(size_t i=first;i<zero.size();++i)
            for(size_t j=0;j<=i;++j) join(zero[i],zero[j],1);
        for(size_t i=0;i<one.size();++i) {
            if(nodes[one[i]].cost!=1) continue;
            for(size_t j=(i<old1?first:0);j<zero.size();++j) join(one[i],zero[j],2);
        }
        if(staged) return;
        for(int price=0;price<3;++price) {
            auto &added=fresh[price], &old=near[price];
            if(added.empty()) continue;
            sort(added.begin(),added.end());
            if(old.empty()) { old.swap(added); continue; }
            size_t boundary=old.size();
            old.insert(old.end(),added.begin(),added.end());
            inplace_merge(old.begin(),old.begin()+boundary,old.end());
            added.clear();
        }
        if(join_mode&2) {
            columns.clear(); columns.resize(moduli.size());
            for(size_t j=0;j<moduli.size();++j) {
                int m=moduli[j];
                if(index.get(m)<0) continue;
                columns[j].resize(m);
                // A value's price is read from the current graph. Keeping the
                // values in numeric order permits conditional nearest neighbors.
                for(const auto &entry:near[2]) columns[j][entry.first%m].push_back(entry.second);
            }
        }
    }
    void stage(const vector<Int>& values) {
        if(staged) throw runtime_error("nested dictionary transaction");
        n_before=nodes.size(); zero_before=zero.size(); one_before=one.size();
        slots_before=index.used.size(); paid_before=paid_mask;
        staged=true;
        for(Int v:values) {
            auto it=scaffold.find(v);
            if(it!=scaffold.end()) paid_mask|=it->second;
        }
        extend(values);
    }
    void rollback() {
        for(auto it=undo.rbegin();it!=undo.rend();++it) {
            nodes[it->id]=it->expr;
            if(join_mode&64) masks[it->id]=it->mask;
        }
        undo.clear();
        while(index.used.size()>slots_before) {
            index.keys[index.used.back()]=0;
            index.used.pop_back();
        }
        nodes.resize(n_before); zero.resize(zero_before); one.resize(one_before);
        if(join_mode&64) masks.resize(n_before);
        for(auto &v:fresh) v.clear();
        missing_three.clear(); paid_mask=paid_before; staged=false;
    }
    int third(Int x) {
        if(x<1 || x>limit) return -1;
        int known=index.get(x);
        if(known>=0 || missing_three.count(x)) return known;
        int left=-1,right=-1;
        char op=0;
        auto try_join=[&](Int y,int id,char operation,bool reverse) {
            if(op || y<1 || y>limit) return;
            int j=index.get(y);
            if(j>=0 && nodes[j].cost+nodes[id].cost<=2) {
                left=reverse?j:id; right=reverse?id:j; op=operation;
            }
        };
        for(int i:zero) {
            Int a=nodes[i].v;
            if(a<x) try_join(x-a,i,'+',false);
            if(a>x) try_join(a-x,i,'-',false);
            if(x<=limit-a) try_join(x+a,i,'-',true);
            if(a>1 && x%a==0) try_join(x/a,i,'*',false);
            if(a>x && a%x==0) try_join(a/x,i,'/',false);
            if(a>1 && x<=limit/a) try_join(x*a,i,'/',true);
            if(op) break;
        }
        if(!op) {
            if(missing_three.size()<250000) missing_three.insert(x);
            return -1;
        }
        int id=nodes.size();
        index.insert(x,id);
        nodes.push_back({x,left,right,op,1+nodes[left].cost+nodes[right].cost});
        if(join_mode&64) masks.push_back(masks[left]|masks[right]);
        return id;
    }
    void materialize(int i, Plan &out, unordered_set<Int>& seen) const {
        auto x=nodes[i];
        if(!x.cost || !seen.insert(x.v).second) return;
        materialize(x.a,out,seen); materialize(x.b,out,seen);
        out.push_back({x.v,nodes[x.a].v,nodes[x.b].v,x.op});
    }
};

Int nonlinear_stage(const LiveBank &bank,Int x,int exponent,int shift,
                    Plan &out,unordered_set<Int>& seen) {
    auto emit=[&](char op,Int a,Int b) {
        Int v=apply(op,a,b);
        if(seen.insert(v).second) out.push_back({v,a,b,op});
        return v;
    };
    if(shift>=0) {
        bank.materialize(shift,out,seen);
        return emit('*',x,emit('+',x,bank.nodes[shift].v));
    }
    if(exponent==1) return x;
    Int square=emit('*',x,x);
    if(exponent==2) return square;
    return exponent==3?emit('*',square,x):emit('*',square,square);
}

struct Path {
    Int rem;
    int cost,parent,scale,bias;
    char sign;
    double rank;
    int compound=-1;
    uint64_t mask=0;
    int exponent=1,shift=-1,denominator=-1;
};

struct DeferredStep {int scale,bias,compound; char sign; int exponent=1,shift=-1,denominator=-1;};
struct Demand {
    Int goal;
    int cost,depth;
    array<DeferredStep,3> chain;
};
struct Meetings {
    unordered_map<Int,Demand> first;
    unordered_map<Int,vector<Demand>> shared;
    void add(Int rem,Int goal,int cost,DeferredStep last,int parent,const vector<Path>& path) {
        if(rem<128 || cost>9) return;
        uint64_t h=(uint64_t(rem)*0x9e3779b97f4a7c15ULL)>>56;
        if((rem>(1LL<<36) && h>9) || (rem>(1LL<<23) && h>95)) return;
        auto it=first.find(rem);
        if(it==first.end() && first.size()>=80000) return;
        if(it!=first.end() && it->second.goal==goal && it->second.cost<=cost) return;
        Demand d{}; d.goal=goal;d.cost=cost;d.chain[d.depth++]=last;
        for(int i=parent;path[i].parent>=0;i=path[i].parent) {
            if(d.depth==3) return;
            auto s=path[i];d.chain[d.depth++]={s.scale,s.bias,s.compound,s.sign,s.exponent,s.shift,s.denominator};
        }
        if(it==first.end()) {first.emplace(rem,d);return;}
        auto m=shared.find(rem);
        if(m==shared.end()) {
            if(it->second.goal==goal) it->second=d;
            else shared[rem]={it->second,d};
            return;
        }
        for(auto &entry:m->second) if(entry.goal==goal) {
            if(cost<entry.cost) entry=d;
            return;
        }
        if(m->second.size()<8) m->second.push_back(d);
    }
};

struct TargetSearch {
    LiveBank &bank;
    int width, upper, best_node=-1, terminal=-1;
    double alpha;
    vector<Path> paths, next;
    unordered_map<Int,int> visited;
    vector<tuple<int,int,int>> finishes;
    int alternative_count;
    Meetings *meetings=nullptr;
    Int original=0;
    TargetSearch(LiveBank &d,int width,int ceiling,double alpha,int alternatives=1)
        :bank(d),width(width),upper(ceiling),alpha(alpha),alternative_count(alternatives) {}
    int extra_price(uint64_t mask) const {
        return (__builtin_popcountll(mask&~bank.paid_mask)+1)/2;
    }
    void offer(int parent, Int rem,int scale,int bias,char sign,int compound=-1,
               int exponent=1,int shift=-1,int denominator=-1) {
        if(rem<1 || rem>bank.limit) return;
        int cost=paths[parent].cost;
        if(scale>=0) cost+=1+bank.nodes[scale].cost;
        if(bias>=0) cost+=1+bank.nodes[bias].cost;
        if(compound>=0) cost+=1+(compound==bias?0:bank.nodes[compound].cost);
        if(exponent>1) cost+=exponent==2?1:2;
        if(shift>=0) cost+=2+bank.nodes[shift].cost;
        if(denominator>=0) cost+=1+(denominator==bias || denominator==scale?0:bank.nodes[denominator].cost);
        uint64_t mask=paths[parent].mask;
        int tax=0;
        if(join_mode&64) {
            int before=extra_price(mask);
            if(scale>=0) mask|=bank.masks[scale];
            if(bias>=0) mask|=bank.masks[bias];
            if(compound>=0) mask|=bank.masks[compound];
            if(shift>=0) mask|=bank.masks[shift];
            if(denominator>=0) mask|=bank.masks[denominator];
            tax=extra_price(mask);
            cost+=tax-before;
        }
        int ceiling=upper+(alternative_count>1?2:0);
        if(cost>=ceiling) return;
        int final=bank.index.get(rem);
        if(final>=0) {
            cost+=bank.nodes[final].cost;
            if(join_mode&64) cost+=extra_price(mask|bank.masks[final])-tax;
            if(cost>=ceiling) return;
            if(cost<upper) {upper=cost; terminal=final; best_node=paths.size();}
            if(alternative_count>1 && (int(finishes.size())<alternative_count ||
                                       cost<get<0>(finishes.back()))) {
                finishes.emplace_back(cost,paths.size(),final);
                stable_sort(finishes.begin(),finishes.end());
                if(int(finishes.size())>alternative_count) finishes.pop_back();
            }
            paths.push_back({rem,cost,parent,scale,bias,sign,0,compound,mask,exponent,shift,denominator});
            return;
        }
        if(meetings && rem<paths[parent].rem)
            meetings->add(rem,original,cost,{scale,bias,compound,sign,exponent,shift,denominator},parent,paths);
        if(rem>=paths[parent].rem || cost+3>=ceiling) return;
        double rank=cost+alpha*log2(double(rem));
        if(int(next.size())==width && rank>=next.back().rank) return;
        auto it=visited.find(rem);
        if(it!=visited.end() && it->second<=cost) return;
        for(auto p=next.begin();p!=next.end();++p) if(p->rem==rem) {
            if(p->cost<=cost) return;
            next.erase(p); break;
        }
        auto position=upper_bound(next.begin(),next.end(),rank,
            [](double score,const Path& state){return score<state.rank;});
        next.insert(position,{rem,cost,parent,scale,bias,sign,rank,compound,mask,exponent,shift,denominator});
        if(int(next.size())>width) next.pop_back();
    }
    void offset(int p,Int rem,int id,char sign) {
        if(!rem) return;
        if(bank.index.get(rem)>=0) offer(p,rem,-1,id,sign);
        if((rem&15)==0) {
            int shift=__builtin_ctzll(rem);
            while(shift>=4) {
                int factor=bank.index.get(Int(1)<<shift);
                if(factor>=0) {offer(p,rem>>shift,factor,id,sign);break;}
                --shift;
            }
        }
    }
    void factor(int p,int i) {
        Int v=paths[p].rem, a=bank.nodes[i].v;
        if(a<=1) return;
        offset(p,abs(v-a),i,v>a?'+':'r');
        if(a<=bank.limit-v) offset(p,a+v,i,'-');
        if(a>=v) return;
        Int q=v/a,r=v%a;
        if(!r) {offer(p,q,i,-1,'+');return;}
        int id=bank.index.get(r);
        if(id>=0) offer(p,q,i,id,'+');
        if(a-r<=bank.limit-v) {
            id=bank.index.get(a-r);
            if(id>=0) offer(p,q+1,i,id,'-');
        }
    }
    void near_product(int p,int i) {
        Int v=paths[p].rem, a=bank.nodes[i].v;
        if(a<2 || a>=v/4) return;
        Int q=v/a;
        for(auto &group:bank.near) {
            auto at=lower_bound(group.begin(),group.end(),make_pair(q,-1))-group.begin();
            for(int k=max<long long>(0,at-1);k<min<long long>(group.size(),at+2);++k) {
                auto [b,j]=group[k];
                if(b<2 || b>bank.limit/a) continue;
                Int product=a*b;
                if(product==v) {
                    offer(p,b,i,-1,'+');
                    continue;
                }
                int existing=bank.index.get(product);
                if(existing>=0) offer(p,abs(v-product),-1,existing,v>product?'+':'r');
                else offer(p,abs(v-product),-1,i,v>product?'+':'r',j);
            }
        }
    }
    void deeper_split(int p,int i) {
        Int v=paths[p].rem, a=bank.nodes[i].v;
        if(a<4 || a>=v/3) return;
        Int q=v/a, r=v%a;
        if(!r) return;
        for(int up=0;up<2;++up) {
            if(up && a-r>bank.limit-v) continue;
            Int quotient=q+up, residual=up?a-r:r;
            int id=bank.third(residual);
            if(id>=0) offer(p,quotient,i,id,up?'-':'+');
            int quotient_id=bank.third(quotient);
            if(quotient_id>=0) offer(p,residual,-1,i,up?'r':'+',quotient_id);
        }
    }
    void factored_bias(int p,Int product,int bias,char sign) {
        if(product<8 || product>bank.limit) return;
        auto it=bank.divisor_cache.find(product);
        if(it==bank.divisor_cache.end())
            it=bank.divisor_cache.emplace(product,factors::divisors(product)).first;
        for(auto divisor:it->second) {
            Int d=Int(divisor), q=product/d;
            if(d<2 || d>q) continue;
            int di=bank.index.get(d), qi=bank.index.get(q);
            if(di>=0) offer(p,q,di,bias,sign);
            if(qi>=0 && q!=d) offer(p,d,qi,bias,sign);
            if(di<0 && qi<0 && d>=128 && d<(1<<23) && d*d>=product/1000000) {
                di=bank.third(d);
                if(di>=0) offer(p,q,di,bias,sign);
            }
        }
    }
    void neighboring_factors(int p) {
        Int t=paths[p].rem;
        factored_bias(p,t,-1,'+');
        int count=0;
        for(int i:bank.zero) {
            if(++count>60) break;
            Int a=bank.nodes[i].v;
            if(a!=t) factored_bias(p,abs(t-a),i,t>a?'+':'r');
            if(a<=bank.limit-t) factored_bias(p,t+a,i,'-');
        }
    }
    static Int floor_square(Int n) {
        Int x=Int(sqrt((long double)n));
        while((x+1)*(x+1)<=n) ++x;
        while(x*x>n) --x;
        return x;
    }
    void exact_power(int p,Int n,int bias,char sign) {
        if(n<4) return;
        Int x=floor_square(n);
        if(x*x==n) {
            offer(p,x,-1,bias,sign,-1,2);
            Int fourth=floor_square(x);
            if(fourth*fourth==x) offer(p,fourth,-1,bias,sign,-1,4);
        }
        Int cube=llround(cbrt((long double)n));
        if(cube>1 && cube*cube*cube==n) offer(p,cube,-1,bias,sign,-1,3);
    }
    void power_neighborhood(int p) {
        Int v=paths[p].rem;
        exact_power(p,v,-1,'+');
        auto consider=[&](Int root,Int product,int exponent,int scale,int shift) {
            if(root<=1 || product<2 || product>bank.limit) return;
            Int delta=abs(v-product);
            int b=delta?bank.index.get(delta):-1;
            if(!delta || b>=0) offer(p,root,scale,b,v>=product?'+':'-',-1,exponent,shift);
        };
        // Scale a repeated factor after paying for its construction once.
        for(int i:bank.zero) {
            Int a=bank.nodes[i].v;
            if(a!=v) exact_power(p,abs(v-a),i,v>a?'+':'r');
            if(a<=bank.limit-v) exact_power(p,a+v,i,'-');
            if(v/a>=4) {
                Int root=floor_square(v/a);
                for(Int x=root;x<=root+1;++x) if(x*x<=bank.limit/a)
                    consider(x,x*x*a,2,a==1?-1:i,-1);
                Int k=Int(cbrt((long double)(v/a)));
                for(Int x=max<Int>(2,k-1);x<=k+1;++x) if(x*x*x<=bank.limit/a)
                    consider(x,x*x*x*a,3,a==1?-1:i,-1);
            }
            // Products of neighboring factors reuse the same unknown.
            if(a<=1000000000LL) {
                Int root=(floor_square(a*a+4*v)-a)/2;
                for(Int x=max<Int>(2,root);x<=root+1;++x)
                    if(x<=bank.limit/(x+a)) consider(x,x*(x+a),1,-1,i);
            }
        }
        Int center=floor_square(v);
        for(auto &level:bank.near) {
            auto index=lower_bound(level.begin(),level.end(),make_pair(center,-1))-level.begin();
            for(int j=max<long long>(0,index-2);j<min<long long>(level.size(),index+2);++j) {
                auto [x,id]=level[j];
                if(x<2 || x>bank.limit/x || x*x==v) continue;
                offer(p,abs(v-x*x),-1,id,v>x*x?'+':'r',id);
            }
        }
    }
    void congruent(int p) {
        Int v=paths[p].rem;
        for(size_t j=0;j<bank.columns.size();++j) {
            if(bank.columns[j].empty()) continue;
            Int m=bank.moduli[j];
            int scale=bank.index.get(m);
            if(v<m*2) continue;
            for(int up=0;up<2;++up) {
                auto &bin=bank.columns[j][up?(m-v%m)%m:v%m];
                auto evaluate=[&](int k) {
                    int id=bin[k]; Int a=bank.nodes[id].v;
                    if(up) {
                        if(a<=bank.limit-v) offer(p,(v+a)/m,scale,id,'-');
                    } else if(a!=v) offer(p,abs(v-a)/m,scale,id,v>a?'+':'r');
                };
                int at=lower_bound(bin.begin(),bin.end(),v,[&](int i,Int x) {
                    return bank.nodes[i].v<x;})-bin.begin();
                for(int k=max(0,at-4);k<min(int(bin.size()),at+4);++k) evaluate(k);
                for(int k=0;k<min<int>(3,bin.size());++k) evaluate(k);
            }
        }
    }
    // Work backwards through an exact division. The numerator need not be a
    // cheap dictionary value as long as its affine representation is cheap.
    void rational_routes(int p) {
        Int t=paths[p].rem, max_denominator=bank.limit/t;
        if(max_denominator<2) return;
        vector<int> denominators;
        for(int d:{2,3,4,5,7,8,9,11,13,16,17,19,25,27,31,32,64,81,127,128,256}) {
            if(d>max_denominator) break;
            int id=bank.index.get(d);
            if(id>=0 && bank.nodes[id].cost<=1) denominators.push_back(id);
        }
        for(int i:bank.zero) {
            Int d=bank.nodes[i].v;
            if(d>=2 && d<=max_denominator && d<=8192 &&
               find(denominators.begin(),denominators.end(),i)==denominators.end()) {
                denominators.push_back(i);
                if(denominators.size()>=29) break;
            }
        }
        for(int di:denominators) {
            Int d=bank.nodes[di].v,n=t*d;
            int ni=bank.index.get(n);
            if(ni>=0) offer(p,n,-1,-1,'+',-1,1,-1,di);
            for(auto &level:bank.near) {
                auto pos=lower_bound(level.begin(),level.end(),make_pair(n,-1))-level.begin();
                for(int j=max<long long>(0,pos-2);j<min<long long>(level.size(),pos+2);++j) {
                    auto [a,bias]=level[j];
                    if(a!=n) offer(p,abs(n-a),-1,bias,n>a?'+':'r',-1,1,-1,di);
                }
            }
            for(int si:bank.zero) {
                Int scale=bank.nodes[si].v;
                if(scale<=d || scale>=n) continue;
                Int q=n/scale,r=n%scale;
                if(!r) {offer(p,q,si,-1,'+',-1,1,-1,di);continue;}
                int bi=bank.index.get(r);
                if(bi>=0) offer(p,q,si,bi,'+',-1,1,-1,di);
                if(scale-r<=bank.limit-n) {
                    bi=bank.index.get(scale-r);
                    if(bi>=0) offer(p,q+1,si,bi,'-',-1,1,-1,di);
                }
            }
        }
    }
    void expand(int p) {
        Int v=paths[p].rem;
        for(auto &level:bank.near) {
            auto center=lower_bound(level.begin(),level.end(),make_pair(v,-1))-level.begin();
            for(int k=max<long long>(0,center-3);k<min<long long>(level.size(),center+3);++k) {
                auto [x,i]=level[k]; offer(p,abs(v-x),-1,i,v>x?'+':'r');
            }
        }
        for(int i:bank.zero) {
            factor(p,i);
            if(join_mode&1) near_product(p,i);
            if((join_mode&32) && paths[p].cost<=4) deeper_split(p,i);
        }
        for(int i:bank.one) if(bank.nodes[i].cost==1) factor(p,i);
        if(join_mode&2) congruent(p);
        if((join_mode&1024) && p==0 && !bank.staged) neighboring_factors(p);
        if((join_mode&2048) && paths[p].cost<=6) power_neighborhood(p);
        if((join_mode&8192) && paths[p].cost<=7) rational_routes(p);
    }
    Plan run(Int target,int depth_limit=14) {
        original=target;
        paths.push_back({target,0,-1,-1,-1,'+',0});
        int direct=bank.index.get(target);
        if(direct>=0) {
            best_node=0; terminal=direct; upper=bank.nodes[direct].cost;
            if(join_mode&64) upper+=extra_price(bank.masks[direct]);
        }
        if(direct<0 || ((join_mode&64) && upper>2)) {
            vector<int> frontier{0};
            for(int depth=0;depth<depth_limit && !frontier.empty();++depth) {
                next.clear();
                int extra=alternative_count>1?2:0;
                for(int p:frontier) if(paths[p].cost+3<upper+extra) expand(p);
                frontier.clear();
                for(auto state:next) if(state.cost+3<upper+extra) {
                    visited[state.rem]=state.cost; frontier.push_back(paths.size()); paths.push_back(state);
                }
            }
        }
        return reconstruct(target,best_node,terminal);
    }
    Plan reconstruct(Int target,int last_node,int last_id) {
        Plan out;
        if(last_node<0) return out;
        unordered_set<Int> seen;
        bank.materialize(last_id,out,seen);
        Int v=bank.nodes[last_id].v;
        for(int p=last_node;paths[p].parent>=0;p=paths[p].parent) {
            auto s=paths[p];
            v=nonlinear_stage(bank,v,s.exponent,s.shift,out,seen);
            if(s.scale>=0) {
                bank.materialize(s.scale,out,seen); Int a=bank.nodes[s.scale].v;
                Int product=v*a;
                if(seen.insert(product).second) out.push_back({product,v,a,'*'});
                v=product;
            }
            if(s.bias>=0) {
                bank.materialize(s.bias,out,seen); Int a=bank.nodes[s.bias].v;
                if(s.compound>=0) {
                    bank.materialize(s.compound,out,seen);
                    Int b=bank.nodes[s.compound].v, product=a*b;
                    if(seen.insert(product).second) out.push_back({product,a,b,'*'});
                    a=product;
                }
                Int left=s.sign=='r'?a:v, right=s.sign=='r'?v:a;
                char op=s.sign=='r'?'-':s.sign;
                v=apply(op,left,right);
                if(seen.insert(v).second) out.push_back({v,left,right,op});
            }
            if(s.denominator>=0) {
                bank.materialize(s.denominator,out,seen);
                Int d=bank.nodes[s.denominator].v, before=v;
                if(v%d) throw runtime_error("nonintegral lifted path");
                v/=d;
                if(seen.insert(v).second) out.push_back({v,before,d,'/'});
            }
        }
        if(v!=target) throw runtime_error("invalid expression reconstruction");
        return out;
    }
};

using Trace=map<Int,Edge>;
Plan trace_plan(Int target,const Trace &trace,const Puzzle &p) {
    Plan result;
    unordered_set<Int> seen;
    auto visit=[&](auto &&self,Int v)->void {
        if(p.defs.count(v) || !seen.insert(v).second) return;
        const auto &e=trace.at(v);
        self(self,e.a); self(self,e.b); result.push_back(e);
    };
    visit(visit,target);
    return result;
}
void commit(Puzzle &p,const Plan &plan) {
    for(const auto &e:plan) {
        if(!p.defs.count(e.a) || !p.defs.count(e.b)) throw runtime_error("undefined ghost operand");
        if(p.make(e.op,e.a,e.b)!=e.out) throw runtime_error("corrupt recipe");
    }
}
Plan incremental(Plan plan,const Puzzle &p) {
    plan.erase(remove_if(plan.begin(),plan.end(),[&](const Edge&e){return p.defs.count(e.out);}),plan.end());
    return plan;
}
vector<Int> working_set(const Puzzle &p,const Trace &warm,const vector<Int> &pending,
                        int budget,mt19937 &rng) {
    map<Int,double> weights;
    for(size_t i=0;i<p.starts.size();++i)
        weights[p.starts[i]]+=1000+double(p.starts.size()-i)/max<size_t>(1,p.starts.size());
    for(Int v:p.palette) weights[v]+=10;
    for(size_t i=0;i<p.order.size();++i) {
        Int v=p.order[i];
        weights[v]+=3.5*double(i+1)/max<size_t>(1,p.order.size())+
                    double(rng()%1000)/2000.0;
        auto it=p.uses.find(v);
        if(it!=p.uses.end()) weights[v]+=min(8.0,1.7*log2(1.+it->second));
    }
    if(!warm.empty()) {
        for(Int t:pending) for(const auto &edge:trace_plan(t,warm,p)) {
            if(p.defs.count(edge.a)) weights[edge.a]+=2;
            if(p.defs.count(edge.b)) weights[edge.b]+=2;
        }
    }
    vector<pair<double,Int>> order;
    for(auto item:weights) order.emplace_back(-item.second,item.first);
    sort(order.begin(),order.end());
    vector<Int> values;
    for(auto item:order) {
        if(int(values.size())==budget) break;
        values.push_back(item.second);
    }
    return values;
}

struct Candidate {Int target; Plan plan; double priority;};

Plan build_branch(const LiveBank &bank,Int value,const Demand &d) {
    Plan out;
    unordered_set<Int> seen{value};
    auto emit=[&](char op,Int a,Int b) {
        Int v=apply(op,a,b);
        if(seen.insert(v).second) out.push_back({v,a,b,op});
        return v;
    };
    for(int i=0;i<d.depth;++i) {
        auto s=d.chain[i];
        value=nonlinear_stage(bank,value,s.exponent,s.shift,out,seen);
        if(s.scale>=0) {
            bank.materialize(s.scale,out,seen);
            value=emit('*',value,bank.nodes[s.scale].v);
        }
        if(s.bias>=0) {
            bank.materialize(s.bias,out,seen);
            Int a=bank.nodes[s.bias].v;
            if(s.compound>=0) {
                bank.materialize(s.compound,out,seen);
                a=emit('*',a,bank.nodes[s.compound].v);
            }
            value=s.sign=='r'?emit('-',a,value):emit(s.sign,value,a);
        }
        if(s.denominator>=0) {
            bank.materialize(s.denominator,out,seen);
            value=emit('/',value,bank.nodes[s.denominator].v);
        }
    }
    if(value!=d.goal) throw runtime_error("joint inverse path did not meet its target");
    return out;
}

// A value in the speculative scaffold can be offered to the search before
// its ancestors are paid for. Charge their exact union when selecting a target.
Plan unpaid_cone(Int t,const Plan &plan,const Puzzle &p,const unordered_set<Int>& paid) {
    unordered_map<Int,Edge> newdefs;
    for(auto e:plan) newdefs[e.out]=e;
    unordered_set<Int> seen;
    Plan out;
    auto visit=[&](auto &&self,Int v)->void {
        if(paid.count(v) || !seen.insert(v).second) return;
        Edge e;
        if(p.defs.count(v)) {
            auto [a,b]=p.args.at(v); e={v,a,b,p.defs.at(v).op};
        } else e=newdefs.at(v);
        self(self,e.a);self(self,e.b);out.push_back(e);
    };
    visit(visit,t);
    return out;
}
int immediate(Int target,Int v,LiveBank &bank) {
    int best=20;
    auto probe=[&](Int x,int base) {
        if(x<1 || x>bank.limit) return;
        int id=bank.index.get(x);
        if(id>=0) best=min(best,base+bank.nodes[id].cost);
    };
    if(target==v) return 0;
    probe(abs(target-v),1);
    if(target<=bank.limit-v) probe(target+v,1);
    if(target%v==0) probe(target/v,1);
    if(v%target==0) probe(v/target,1);
    if(v>1 && target>v) {
        Int q=target/v,r=target%v;
        if(r) for(int upper=0;upper<2;++upper) {
            if(upper && v-r>bank.limit-target) continue;
            int qid=bank.index.get(q+upper), rid=bank.index.get(upper?v-r:r);
            if(qid>=0 && rid>=0) best=min(best,2+bank.nodes[qid].cost+bank.nodes[rid].cost);
        }
    }
    return best;
}

// Factor nearby exact integers, then synthesize *both* operands. Neither
// factor has to occur in the current two-instruction dictionary.
vector<Plan> branching_products(Int t,LiveBank &bank,int ceiling,double alpha){
    struct Split {double rank;Int x,y,n;int bias;char sign;};
    vector<Split> candidates;
    unordered_map<Int,double> estimates;
    auto estimate=[&](Int x){
        auto prev=estimates.find(x);if(prev!=estimates.end())return prev->second;
        int direct=bank.index.get(x);
        double best=direct>=0?bank.nodes[direct].cost:3.0+.12*log2(double(x));
        if(direct<0){
            for(int c=0;c<2;++c){
                auto &level=bank.near[c];auto pos=lower_bound(level.begin(),level.end(),make_pair(x,-1))-level.begin();
                for(int k=max<long long>(0,pos-2);k<min<long long>(level.size(),pos+2);++k){
                    int id=bank.index.get(abs(x-level[k].first));
                    if(id>=0)best=min(best,1.+c+bank.nodes[id].cost);
                }
            }
        }
        estimates.emplace(x,best);return best;
    };
    auto factors_for=[&](Int n,int bias,char sign){
        if(n<6||n>bank.limit)return;
        auto it=bank.divisor_cache.find(n);
        if(it==bank.divisor_cache.end())it=bank.divisor_cache.emplace(n,factors::divisors(n)).first;
        for(auto divisor:it->second){
            Int x=Int(divisor),y=n/x;
            if(x<3||x>y)continue;
            double e=estimate(x)+(x==y?0:estimate(y))+1+(bias<0?0:1+bank.nodes[bias].cost);
            if(e>ceiling+2)continue;
            candidates.push_back({e,x,y,n,bias,sign});
        }
    };
    factors_for(t,-1,'+');
    int n=0;
    for(int b:bank.zero){
        Int a=bank.nodes[b].v;
        if(a==t)continue;
        factors_for(abs(t-a),b,t>a?'+':'r');
        if(a<=bank.limit-t)factors_for(t+a,b,'-');
        if(++n>=44)break;
    }
    sort(candidates.begin(),candidates.end(),[](const Split&a,const Split&b){
        return tie(a.rank,a.n,a.x)<tie(b.rank,b.n,b.x);});
    unordered_map<Int,pair<bool,Plan>> cache;
    auto required=[&](Int x)->const pair<bool,Plan>&{
        auto it=cache.find(x);
        if(it==cache.end()){
            TargetSearch inner(bank,3,min(ceiling,13),alpha);
            auto plan=inner.run(x,9);
            it=cache.emplace(x,make_pair(inner.best_node>=0,move(plan))).first;
        }
        return it->second;
    };
    vector<Plan> output;
    int tested=0,reviewed=0;
    for(auto &c:candidates){
        if(++reviewed>70 || cache.size()>75)break;
        auto &a=required(c.x);if(!a.first)continue;
        auto &b=required(c.y);if(!b.first)continue;
        Plan plan;unordered_set<Int> seen;
        auto add=[&](Edge e){if(seen.insert(e.out).second)plan.push_back(e);};
        for(auto e:a.second)add(e);for(auto e:b.second)add(e);
        add({c.n,c.x,c.y,'*'});
        if(c.bias>=0){
            bank.materialize(c.bias,plan,seen);
            Int offset=bank.nodes[c.bias].v;
            if(c.sign=='r')add({t,offset,c.n,'-'});
            else add({t,c.n,offset,c.sign});
        }
        if(int(plan.size())<ceiling+2)output.push_back(move(plan));
        if(++tested>=16 || cache.size()>75)break;
    }
    return output;
}

// Choose a small puzzle-specific starting dictionary. A candidate has to
// improve a decomposition of at least one still poorly represented target;
// several nearly interchangeable multipliers do not all receive the same credit.
void custom_palette(Puzzle &p,mt19937 &rng) {
    if(!p.defs.count(1)) p.make('/',p.starts[0],p.starts[0]);
    p.palette={1};
    for(int k:{1,2,3,4,5,6,8,10,16,20,32})
        if((Int(1)<<k)<=p.limit) p.palette.push_back(p.power(k));
    for(int v:{3,5,7,11}) if(v<=p.limit) p.palette.push_back(p.binary(v));
    vector<Int> core=p.starts;
    for(Int x:p.palette) if(x<=65536) core.push_back(x);
    LiveBank pool(p.limit,350000);
    pool.extend(core);
    auto price=[&](Int x) -> double {
        if(!x) return -1;
        int id=pool.index.get(x);
        if(id>=0) return pool.nodes[id].cost;
        double bits=log2(double(x)+1.0);
        double score=2.1+.118*bits;
        for(int level=0;level<2;++level) {
            auto &values=pool.near[level];
            auto it=lower_bound(values.begin(),values.end(),make_pair(x,-1));
            for(int k=0;k<2;++k) {
                if(k) {if(it==values.begin()) break;--it;}
                if(it==values.end()) continue;
                Int gap=abs(x-it->first);
                int gid=pool.index.get(gap);
                if(gid>=0) score=min(score,level+1.0+pool.nodes[gid].cost);
            }
        }
        return score;
    };
    auto project=[&](Int t,Int h) {
        double best=20;
        if(h<=1) return best;
        if(t!=h) best=min(best,1+price(abs(t-h)));
        if(h>t) return best;
        Int q=t/h,r=t%h;
        if(!r) best=min(best,1+price(q));
        else {
            best=min(best,2+price(q)+price(r));
            if(h-r<=p.limit-t) best=min(best,2+price(q+1)+price(h-r));
        }
        return best;
    };
    vector<int> choices=pool.one;
    vector<int> deeper;
    for(int id=0;id<int(pool.nodes.size());++id)
        if(pool.nodes[id].cost==2 && pool.nodes[id].v>=9 && !p.defs.count(pool.nodes[id].v))
            deeper.push_back(id);
    shuffle(deeper.begin(),deeper.end(),rng);
    if(deeper.size()>520) deeper.resize(520);
    choices.insert(choices.end(),deeper.begin(),deeper.end());
    vector<double> current(p.targets.size(),16.0);
    for(size_t i=0;i<p.targets.size();++i)
        for(Int h:core) current[i]=min(current[i],project(p.targets[i],h));
    vector<vector<double>> costs;
    for(int id:choices) {
        vector<double> row;
        for(Int t:p.targets) row.push_back(project(t,pool.nodes[id].v));
        costs.push_back(move(row));
    }
    for(int round=0;round<12;++round) {
        double top=.18; int selected=-1;
        for(size_t j=0;j<choices.size();++j) {
            const auto& x=pool.nodes[choices[j]];
            if(p.defs.count(x.v)) continue;
            double gain=-.42*x.cost;
            for(size_t i=0;i<p.targets.size();++i)
                gain+=min(2.6,max(0.,current[i]-costs[j][i]));
            if(gain>top) {top=gain;selected=j;}
        }
        if(selected<0) break;
        Plan recipe; unordered_set<Int> seen;
        pool.materialize(choices[selected],recipe,seen);
        commit(p,recipe);
        p.palette.push_back(pool.nodes[choices[selected]].v);
        for(size_t i=0;i<current.size();++i) current[i]=min(current[i],costs[selected][i]);
    }
}

void plan_puzzle(Puzzle &p,const Trace &warm,const vector<Int> &warmOrder,int tail,
                 int leaf_budget,int scan,int width,double alpha,double lookahead,
                 int style,mt19937 &rng) {
    for(Int v:p.starts) p.defs[v]={v};
    vector<Int> pending=p.targets;
    if(!warm.empty() && tail==0 && style>=3) {
        map<Int,uint64_t> coverage;
        set<Int> goals(p.targets.begin(),p.targets.end());
        for(size_t i=0;i<p.targets.size();++i) coverage[p.targets[i]]|=uint64_t(1)<<i;
        map<Int,int> consumers;
        for(auto it=warmOrder.rbegin();it!=warmOrder.rend();++it) {
            auto e=warm.at(*it);
            coverage[e.a]|=coverage[e.out]; coverage[e.b]|=coverage[e.out];
            ++consumers[e.a]; if(e.a!=e.b) ++consumers[e.b];
        }
        int threshold=style==3?2:style==4?4:6;
        for(Int v:warmOrder) {
            if(goals.count(v) || __builtin_popcountll(coverage[v])<threshold) continue;
            if(style==6 && consumers[v]<3) continue;
            commit(p,trace_plan(v,warm,p));
        }
    }
    if(!warm.empty() && tail>0 && int(pending.size())>tail) {
        if(style==0) {
            map<Int,int> position; for(size_t i=0;i<warmOrder.size();++i) position[warmOrder[i]]=i+1;
            stable_sort(pending.begin(),pending.end(),[&](Int a,Int b){return position[a]<position[b];});
        } else if(style==1) shuffle(pending.begin(),pending.end(),rng);
        else {
            // Keep interdependent targets together. Shared intermediates may be
            // replaced jointly when the whole group is released.
            vector<unordered_set<Int>> footprints;
            for(Int x:pending) {
                footprints.emplace_back();
                for(auto edge:trace_plan(x,warm,p)) footprints.back().insert(edge.out);
            }
            int first=rng()%pending.size();
            vector<pair<double,Int>> overlap;
            for(size_t j=0;j<pending.size();++j) {
                double similarity=0;
                for(auto v:footprints[j]) if(footprints[first].count(v)) similarity+=1;
                similarity/=sqrt(double(1+footprints[j].size()));
                overlap.emplace_back(similarity+double(rng()%1000)/5000.,pending[j]);
            }
            sort(overlap.begin(),overlap.end());
            for(size_t j=0;j<pending.size();++j) pending[j]=overlap[j].second;
        }
        size_t frozen=pending.size()-tail;
        for(size_t i=0;i<frozen;++i) commit(p,trace_plan(pending[i],warm,p));
        pending.erase(pending.begin(),pending.begin()+frozen);
    }
    // Make the handmade scaffold available after preserving the warm dependencies.
    // A shared constant may have a cheaper puzzle-specific recipe in the warm DAG.
    unordered_set<Int> paid(p.starts.begin(),p.starts.end());
    for(Int v:p.order) paid.insert(v);
    if(join_mode&16) {
        if(!p.defs.count(1)) p.make('/',p.starts[0],p.starts[0]);
        p.palette={1};
    } else if(join_mode&512) custom_palette(p,rng);
    else p.setup();
    LiveBank bank(p.limit,1800000);
    if(join_mode&64) {
        int bit=0;
        for(Int v:p.order) if(!paid.count(v)) {
            auto [a,b]=p.args.at(v);
            uint64_t required=bank.scaffold[a]|bank.scaffold[b];
            if(bit<64) required|=uint64_t(1)<<bit++;
            bank.scaffold[v]=required;
        }
    }
    auto discard_done=[&] {
        pending.erase(remove_if(pending.begin(),pending.end(),
                      [&](Int x){return p.defs.count(x);}),pending.end());
    };
    discard_done();
    if(pending.empty()) return;
    // Rebuild a reproducible subset using synthetic routes. The rest keeps the
    // donor backbone so different runs retain compatible shared intermediates.
    set<Int> explore;
    if((join_mode&4096) && !warm.empty()) {
        auto shuffled=pending;
        shuffle(shuffled.begin(),shuffled.end(),rng);
        explore.insert(shuffled.begin(),shuffled.begin()+(2*shuffled.size()+2)/3);
    }
    bank.extend(working_set(p,warm,pending,leaf_budget,rng));
    while(!pending.empty()) {
        vector<Candidate> candidates;
        vector<pair<int,Int>> shortlist;
        map<Int,vector<pair<Int,int>>> demands;
        Meetings meetings;
        auto admit=[&](Int t,Plan plan) {
            if(join_mode&4) plan=unpaid_cone(t,plan,p,paid);
            auto cost=plan.size();
            if(cost) candidates.push_back({t,move(plan),double(cost)});
            return int(cost);
        };
        for(Int t:pending) {
            int ceiling=40;
            Plan fallback;
            if(!warm.empty()) {
                Plan donor=trace_plan(t,warm,p);
                if(explore.count(t)) {
                    fallback=(join_mode&4)?unpaid_cone(t,donor,p,paid):move(donor);
                    ceiling=min(ceiling,int(fallback.size())+6);
                } else ceiling=min(ceiling,admit(t,donor)+4);
            }
            TargetSearch quick(bank,scan,ceiling,alpha);
            if((join_mode&256) && pending.size()>1) quick.meetings=&meetings;
            auto plan=incremental(quick.run(t),p);
            if(!plan.empty()) {
                int length=admit(t,move(plan));
                shortlist.emplace_back(length,t);
                if(!fallback.empty() && length>int(fallback.size())+5)
                    admit(t,move(fallback));
            } else {
                shortlist.emplace_back(99,t);
                if(!fallback.empty()) admit(t,move(fallback));
            }
            if(join_mode&8) {
                map<Int,int> unique;
                for(auto &state:quick.paths) {
                    auto it=unique.find(state.rem);
                    if(it==unique.end() || state.cost<it->second) unique[state.rem]=state.cost;
                }
                demands[t].assign(unique.begin(),unique.end());
            }
        }
        sort(shortlist.begin(),shortlist.end());
        if(join_mode&16384){
            int explored=0;
            for(auto [upper,t]:shortlist){
                if(t<10000||upper<6)continue;
                for(auto &plan:branching_products(t,bank,min(upper+2,16),alpha))
                    admit(t,move(plan));
                if(++explored>=3)break;
            }
        }
        if(width>scan) for(size_t i=0;i<min<size_t>(shortlist.size(),4);++i) {
            auto [upper,t]=shortlist[i];
            TargetSearch deep(bank,width,min(40,upper+2),alpha,join_mode&8?4:1);
            auto plan=incremental(deep.run(t),p);
            if(!plan.empty()) admit(t,move(plan));
            for(auto [price,node,id]:deep.finishes) if(node!=deep.best_node) {
                auto alt=incremental(deep.reconstruct(t,node,id),p);
                if(!alt.empty()) admit(t,move(alt));
            }
        }
        vector<Int> added;
        if(candidates.empty()) {
            size_t old=p.order.size(); p.binary(pending.front());
            added.assign(p.order.begin()+old,p.order.end());
        } else {
            map<Int,int> cheapest;
            for(auto &c:candidates) {
                auto it=cheapest.find(c.target);
                if(it==cheapest.end() || int(c.plan.size())<it->second) cheapest[c.target]=c.plan.size();
            }
            if((join_mode&256) && !meetings.shared.empty()) {
                vector<pair<double,Int>> keys;
                for(auto &entry:meetings.shared) {
                    double saving=0;
                    for(auto &d:entry.second)
                        if(cheapest.count(d.goal)) saving+=max(0,cheapest.at(d.goal)-d.cost);
                    if(saving>=3) keys.emplace_back(saving-.14*log2(double(entry.first)),entry.first);
                }
                sort(keys.rbegin(),keys.rend());
                for(size_t j=0;j<min<size_t>(keys.size(),16);++j) {
                    Int value=keys[j].second;
                    TargetSearch inner(bank,max(2,scan),15,alpha);
                    Plan joint=inner.run(value);
                    if(joint.empty()) continue;
                    auto branches=meetings.shared.at(value);
                    sort(branches.begin(),branches.end(),[&](const Demand&a,const Demand&b){
                        return cheapest[a.goal]-a.cost>cheapest[b.goal]-b.cost;});
                    unordered_set<Int> known;
                    for(auto e:joint) known.insert(e.out);
                    vector<Int> hit;
                    for(auto &d:branches) {
                        auto branch=build_branch(bank,value,d);
                        int extra=0;
                        for(auto e:branch) extra+=!known.count(e.out) && !p.defs.count(e.out);
                        if(extra>=cheapest[d.goal]) continue;
                        for(auto e:branch) if(!p.defs.count(e.out) && known.insert(e.out).second)
                            joint.push_back(e);
                        hit.push_back(d.goal);
                    }
                    if(hit.size()<2) continue;
                    Plan paid_joint;
                    known.clear();
                    for(Int t:hit) for(auto e:unpaid_cone(t,joint,p,paid))
                        if(known.insert(e.out).second) paid_joint.push_back(e);
                    int sum=0, largest=0;
                    for(Int t:hit) {sum+=cheapest[t];largest=max(largest,cheapest[t]);}
                    if(int(paid_joint.size())>=sum) continue;
                    // Credit the other newly completed targets at their current cost.
                    // The normal lookahead will account for the same goals at its own weight.
                    double price=paid_joint.size()-(1-lookahead)*(sum-cheapest[hit[0]]);
                    candidates.push_back({hit[0],move(paid_joint),price});
                }
            }
            if(lookahead>0) for(auto &c:candidates) {
                double benefit=0;
                for(auto [t,price]:cheapest) if(t!=c.target) {
                    int next=price, shared=0;
                    for(auto &e:c.plan) next=min(next,immediate(t,e.out,bank));
                    if(join_mode&8) for(auto [res,cost]:demands[t]) {
                        if(cost+1>=next || res==t) continue;
                        for(auto &e:c.plan)
                            next=min(next,cost+immediate(res,e.out,bank));
                    }
                    for(auto &r:candidates) if(r.target==t && int(r.plan.size())==price) {
                        int overlap=0;
                        for(auto &e:c.plan) for(auto &f:r.plan) if(e.out==f.out) {++overlap;break;}
                        shared=max(shared,overlap);
                    }
                    benefit+=max(price-next, shared);
                }
                c.priority-=lookahead*benefit;
            }
            if((join_mode&128) && candidates.size()>1 && pending.size()>2) {
                stable_sort(candidates.begin(),candidates.end(),[](const Candidate &a,
                            const Candidate &b){return a.priority<b.priority;});
                vector<Candidate> finalists;
                set<vector<Int>> paths;
                for(auto &c:candidates) {
                    vector<Int> v;
                    for(auto e:c.plan) v.push_back(e.out);
                    sort(v.begin(),v.end());
                    if(!paths.insert(v).second) continue;
                    finalists.push_back(c);
                    if(finalists.size()>=4) break;
                }
                for(auto &c:finalists) {
                    vector<Int> made;
                    unordered_set<Int> present;
                    for(auto e:c.plan) {made.push_back(e.out);present.insert(e.out);}
                    bank.stage(made);
                    double benefit=0;
                    for(auto [t,previous]:cheapest) if(t!=c.target) {
                        int price=previous;
                        for(auto &r:candidates) if(r.target==t) {
                            int cost=0;
                            for(auto e:r.plan) cost+=!present.count(e.out);
                            price=min(price,cost);
                        }
                        if(price>2) {
                            TargetSearch probe(bank,1,price,alpha);
                            probe.run(t,2);
                            if(probe.best_node>=0) price=min(price,probe.upper);
                        }
                        benefit+=previous-price;
                    }
                    bank.rollback();
                    c.priority=c.plan.size()-lookahead*benefit;
                }
                candidates.swap(finalists);
            }
            auto selected=min_element(candidates.begin(),candidates.end(),
                [](const Candidate &a,const Candidate &b){return a.priority<b.priority;});
            commit(p,selected->plan);
            for(auto &edge:selected->plan) added.push_back(edge.out);
        }
        for(Int v:added) {
            paid.insert(v);
            if(join_mode&64) {
                auto it=bank.scaffold.find(v);
                if(it!=bank.scaffold.end()) bank.paid_mask|=it->second;
            }
        }
        discard_done();
        if(pending.empty()) break;
        if(int(bank.zero.size()+added.size())>leaf_budget+16) {
            bank.reset();
            added=working_set(p,warm,pending,leaf_budget,rng);
        }
        bank.extend(added);
    }
}

#ifndef SANTA_VIRTUAL_LIBRARY
int main(int argc,char **argv) {
    if(argc!=9 && argc!=10) return 2;
    if(argc==10) join_mode=stoi(argv[9]);
    int leaves=stoi(argv[1]), scan=stoi(argv[2]), width=stoi(argv[3]),tail=stoi(argv[6]),
        style=stoi(argv[7]),seed=stoi(argv[8]);
    double alpha=stod(argv[4]), lookahead=stod(argv[5]);
    TARGET_LEAVES=true;
    string id; Int limit; int ns,nt;
    while(cin>>id>>limit>>ns>>nt) {
        Puzzle p(limit,width);
        p.starts.resize(ns);p.targets.resize(nt);
        for(auto &x:p.starts) cin>>x;
        for(auto &x:p.targets) cin>>x;
        int n;cin>>n; Trace warm;vector<Int> order;
        for(int i=0;i<n;++i) {
            Edge edge;cin>>edge.out>>edge.op>>edge.a>>edge.b;
            warm.emplace(edge.out,edge);order.push_back(edge.out);
        }
        mt19937 rng(seed^uint32_t(hash<string>{}(id)));
        plan_puzzle(p,warm,order,tail,leaves,scan,width,alpha,lookahead,style,rng);
        cout<<id<<" "<<p.order.size()<<"\n";
        for(Int v:p.order) {
            auto [a,b]=p.args.at(v);
            cout<<v<<" "<<p.defs.at(v).op<<" "<<a<<" "<<b<<"\n";
        }
        cout<<flush;
    }
    return 0;
}
#endif
