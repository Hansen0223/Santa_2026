"""Build the dense proof engine with optional fourth-level sharding."""
import argparse
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / "proofs/local/work/gpu/closest-36729"


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Expected exactly one source anchor: {old}")
    return text.replace(old, new)


def build(cxx, out):
    driver = (SOURCE / "hot.cpp").read_text(encoding="utf8")
    dense = (SOURCE / "hot_dense.hpp").read_text(encoding="utf8")
    dense = replace_once(dense, "    std::vector<uint64_t> words, occupied;", """    unsigned fourth_part = 0, fourth_parts = 1;
    bool elsewhere(std::size_t depth, unsigned& index) const {
        if (depth == 3 && fourth_parts > 1)
            return index++ % fourth_parts != fourth_part;
        return Search::elsewhere(depth, index);
    }
    std::vector<uint64_t> words, occupied;""")
    dense = replace_once(dense, "(helpers.size()==2 && shards_three>1);",
                         "(helpers.size()==2 && shards_three>1) || (helpers.size()==3 && fourth_parts>1);")
    driver = replace_once(driver, '#include "hot_dense.hpp"', '#include "hot_fourth_dense.hpp"')
    driver = replace_once(driver, "    unsigned n,m,h;", """    if (argc == 10) {
        s.fourth_part=std::stoul(argv[8]);s.fourth_parts=std::stoul(argv[9]);
        if (!s.fourth_parts || s.fourth_part>=s.fourth_parts) return 2;
    }
    unsigned n,m,h;""")
    driver = replace_once(driver, "(s.shards_three>1 && h<5))",
                          "(s.shards_three>1 && h<5) || (s.fourth_parts>1 && h<6))")
    driver = replace_once(driver, "if (argc!=8 ||", "if ((argc!=8 && argc!=10) ||")
    out = out.resolve()
    if not out.parent.is_dir():
        raise ValueError("Create the output directory first")
    with TemporaryDirectory(dir=out.parent) as tmp:
        directory = Path(tmp)
        (directory / "hot_fourth_dense.hpp").write_text(dense,encoding="utf8")
        source = directory / "hot_fourth.cpp"
        source.write_text(driver,encoding="utf8")
        subprocess.run([cxx,"-O3","-std=c++17","-static","-Wl,--no-insert-timestamp",
                        "-I",str(SOURCE),str(source),"-o",str(out)],
                       env={**os.environ,"TMP":tmp,"TEMP":tmp},check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cxx",default="g++")
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    build(args.cxx,args.out)


if __name__=="__main__":
    main()
