// Join two short multiplicative expressions on an exact sum, difference or ratio.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <unordered_map>
#include <vector>

using Value = std::int64_t;
struct Node { Value v; char op; int a,b,cost; };
using Path = std::vector<Node>;

class Dictionary {
    Value limit, target;
    int budget;
    std::unordered_map<Value,int> index;
    std::vector<Node> nodes;
    std::map<int,std::vector<Path>> best;
    int found=0;

    void add(Value v, char op, int a, int b, int cost) {
        if (v==target || v<=0 || v>limit || index.count(v)) return;
        index.emplace(v,int(nodes.size()));
        nodes.push_back({v,op,a,b,cost});
    }
    void products(int a,int b) {
        Value x=nodes[a].v, y=nodes[b].v;
        int cost=1+nodes[a].cost+(a==b?0:nodes[b].cost);
        if (x<=limit/y) add(x*y,'*',a,b,cost);
        if (x<y) {std::swap(x,y);std::swap(a,b);}
        if (x%y==0) add(x/y,'/',a,b,cost);
    }
    void append(int id,std::vector<int>& plan) const {
        const auto &n=nodes[id];
        if (!n.op || std::find(plan.begin(),plan.end(),id)!=plan.end()) return;
        append(n.a,plan);
        append(n.b,plan);
        plan.push_back(id);
    }
    void join(int a, Value other, char op, bool reverse=false) {
        auto it=index.find(other);
        if (it==index.end()) return;
        int b=it->second;
        if ((op=='+' || op=='*') && a>b) return;
        if (reverse) std::swap(a,b);
        std::vector<int> plan;
        append(a,plan);append(b,plan);
        int cost=1+int(plan.size());
        if (cost>budget || (found>=24 && cost>=best.rbegin()->first)) return;
        Path path;
        for (int id:plan) {
            auto n=nodes[id];path.push_back({n.v,n.op,n.a,n.b,n.cost});
        }
        path.push_back({target,op,a,b,cost});
        best[cost].push_back(std::move(path));
        if (++found>24) {
            auto last=std::prev(best.end());last->second.pop_back();
            if (last->second.empty()) best.erase(last);
            --found;
        }
    }
public:
    Dictionary(Value cap,Value goal,int maxcost):limit(cap),target(goal),budget(maxcost) {}
    void search(const std::vector<Value>& anchors,int second) {
        index.reserve(280000);nodes.reserve(160000);
        for (Value v:anchors) add(v,0,-1,-1,0);
        int paid=int(nodes.size());
        for (int i=0;i<paid;++i) for (int j=0;j<=i;++j) {
            Value x=nodes[i].v,y=nodes[j].v;
            if (x<=limit-y) add(x+y,'+',i,j,1);
            if (x>y) add(x-y,'-',i,j,1);
            if (y>x) add(y-x,'-',j,i,1);
            products(i,j);
        }
        int atoms=int(nodes.size());
        for (int i=paid;i<atoms;++i) for (int j=0;j<paid;++j) products(i,j);
        std::vector<int> order;
        for (int i=paid;i<atoms;++i) order.push_back(i);
        std::sort(order.begin(),order.end(),[&](int a,int b){return nodes[a].v<nodes[b].v;});
        std::vector<int> sampled;
        int count=std::min<int>(order.size(),second);
        for (int j=0;j<count;++j) sampled.push_back(order[j*order.size()/count]);
        for (size_t i=0;i<sampled.size();++i)
            for (size_t j=0;j<=i;++j) products(sampled[i],sampled[j]);
        for (int i=0;i<int(nodes.size());++i) {
            Value x=nodes[i].v;
            if (target>x) join(i,target-x,'+');
            if (x>target) join(i,x-target,'-');
            if (target%x==0) join(i,target/x,'*');
            if (x<=limit/target) join(i,x*target,'/',true);
        }
        std::cout<<nodes.size()<<' '<<found<<'\n';
        for (const auto &[cost,paths]:best) for (const auto &path:paths) {
            std::cout<<path.size()<<'\n';
            for (auto n:path) std::cout<<n.v<<' '<<n.op<<' '<<nodes[n.a].v<<' '<<nodes[n.b].v<<'\n';
        }
    }
};
int main() {
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    Value cap,goal;int n,budget,width;
    while (std::cin>>cap>>goal>>budget>>width>>n) {
        std::vector<Value> anchors(n);
        for (auto &x:anchors) std::cin>>x;
        Dictionary(cap,goal,budget).search(anchors,width);
    }
}
