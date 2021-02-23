#!/usr/bin/env bash
set -uo pipefail

################################################################################
# tce.sh ROOT [SOOT]
# ROOT: Root of project
#
# This procedure does the following:
# 1. Set Up Working Directory
#    (a) Create a working directory $WORK
#    (b) Jar the compiled files
#    (c) Create $COMPILEDMUTANTS, a directory to store compiled classfiles from
#        each mutant
#
# 2. For each mutant in $MUTANTS
#    (a) create a new directory in $COMPILEDMUTANTS
#    (b) find the mutant file...ensure there is exactly 1!
#    (c) compile the mutant file, outputting to the directory we created in 2a
#

function die {
    echo "Die: $1"
    exit 1
}

# BEGIN THE PARSING OF ARGUMENTS
if [ $# -lt 1 ]
then
    die "usage: tce.sh ROOT [SOOT RTJAR] [-d DEPJAR]* [-dd DEPDIR]"
fi

DRYRUN="FALSE"
DEPS=""
PARAMS=""
while (( "$#" )); do
    case "$1" in
        -d|--dependencies)
            if [ -z "$DEPS" ]; then
                DEPS="$(realpath $2)"
            else
                DEPS="$DEPS:$(realpath $2)"
            fi
            shift
            ;;
        -dd|--dependency-dir)
            for f in $(ls $2); do
                if [ -z "$DEPS" ]; then
                    DEPS="$(realpath $f)"
                else
                    DEPS="$DEPS:$(realpath $f)"
                fi
            done
            shift
            ;;
        --dryrun)
            DRYRUN="TRUE"
            ;;
        -*|--*)
            die "Unsupported flag $1. Usage: tce.sh ROOT [SOOT RTJAR] [-d DEPJAR]*"
            echo "Unsupported flag $1" >&2
            exit 1
            ;;
        *)
            PARAMS="$PARAMS $1"
            ;;
    esac
    shift
done
echo "Classpath=$DEPS"

eval set -- "$PARAMS"

if [ $# -eq 1 ]
then
    ROOT=$(realpath "$1")
    echo "ROOT=$ROOT"
elif [ $# -eq 3 ]
then
    ROOT=$(realpath "$1")
    SOOT=$(realpath "$2")
    RT=$(realpath "$3")
    echo "ROOT=$ROOT"
    echo "SOOT=$SOOT"
    echo "RT=$RT"
else
    die "usage: tce.sh ROOT [SOOT RTJAR] [-d DEPJAR]* [-dd DEPDIR]"
fi

# END THE PARSING OF THE ARGS

if [ ! -z $JAVA_HOME ]
then
    echo "Using JAVA_HOME=$JAVA_HOME"
    JAVA="$JAVA_HOME/bin/java"
    JAVAC="$JAVA_HOME/bin/javac"
else
    echo "No JAVA_HOME set...using default java and javac"
    JAVA=java
    JAVAC=javac
fi

MUTANTS="$ROOT/mutants"
echo "JAVA=$JAVA"
echo "JAVAC=$JAVAC"
echo "MUTANTS=$MUTANTS"

if [ "$DRYRUN" == "TRUE" ]; then
    exit 0
fi

function setup-wd {
    # 1a
    WORK=$(mktemp -d "${TMPDIR:-/tmp/}tce.XXXXXXXXXXXX") || die "Failed to create temporary directory "
    echo "Working directory: $WORK"

    # 1c
    COMPILEDMUTANTS="$WORK/compiled-mutants"
    SOOTOUTPUT="$WORK/soot"
    mkdir "$COMPILEDMUTANTS"
}


################################################################################
# Find all classfiles newer than $WORK/timestamp in the given directory
function find-new-classfiles {
    dir="$1"
    find "$dir" -newer "$WORK/timestamp"
}

################################################################################
# This command is to be run on the output of `find`, in particular for finding
# mutants. This runs through `wc` to ensure that there exactly one line was
# returned. If there was another number of found items, die with an error
# message.
function find-exactly-one-mutant {
    mid="$1"
    pushd "$MUTANTS/$mid" >> /dev/null
    found=$(find * -name "*.java")
    count=$(echo "$found" | wc -l)    # Count number of found items
    count=$(echo "$count" | xargs)    # Trim whitespace
    test $count -eq 1 || die "Found multiple mutants in $mid"
    echo "$found"
    popd >> /dev/null
}

function run-on-mutants {
    for mid in $(ls "$MUTANTS")
    do
        printf "\033[1;32mMutant $mid\033[0m\n"
        # 2a
        MDIR="$COMPILEDMUTANTS/$mid"
        mkdir $MDIR

        # 2b
        rel_mutant_file=$(find-exactly-one-mutant $mid)
        echo "    Found mutant file $rel_mutant_file"
        mutant_file="$MUTANTS/$mid/$rel_mutant_file"

        # 2c
        echo "    Compiling"

        if  ! $JAVAC -cp $DEPS -d $MDIR $mutant_file
        then
            echo "Failed to compile mutant " $mid
            echo "$mid $mutant_file" >> "$WORK/tce-failures"
            continue
        fi

        if [ ! -z ${SOOT+x} ]
        then
            mkdir "$SOOTOUTPUT/$mid"
            pushd "$MDIR" > /dev/null
            echo "    Running Soot"
            for cf in $(find * -name "*.class")
            do
                cf=${cf%.class}        # Remove file extension: `org/foo/Bar.class` --> `org/foo/Bar`
                cf=${cf//\//.}         # Replace `/` with `.`:  `org/foo/Bar`       --> `org.foo.Bar`
                if ! $JAVA -jar $SOOT -cp "$MDIR:$DEPS:$RT" $cf -d "$SOOTOUTPUT/$mid"
                then
                    echo "Failed to run soot on mutant " $mid
                    echo "$mid $mutant_file" >> "$WORK/tce-soot-failures"
                    break
                fi
            done
            popd > /dev/null
        fi
    done
    echo "Compiled mutants are located in\n$COMPILEDMUTANTS"
}

function report {
    echo
    echo
    echo "Working Directory: $WORK"
}

trap report EXIT

setup-wd
run-on-mutants
