#!/bin/bash

# Note: Collabora repository with pending patches
# https://git.collabora.com/cgit/linux.git/log/?h=topic/chromeos/waiting-for-upstream

stable_path=$(python -c "from config import stable_path; print stable_path;")
stable_repo=$(python -c  "from config import stable_repo; print stable_repo;")

chromeos_path=$(python -c "from config import chromeos_path; print chromeos_path;")
chromeos_repo=$(python -c  "from config import chromeos_repo; print chromeos_repo;")

upstream_path=$(python -c "from config import upstream_path; print upstream_path;")
if [[ "$(dirname ${upstream_path})" = "." ]]; then
	# Needs to be an absolute path name
	upstream_path="$(pwd)/${upstream_path}"
fi
upstream_repo=$(python -c  "from config import upstream_repo; print upstream_repo;")

sbranches=($(python -c "from config import stable_branches; print stable_branches" | tr -d "(),'"))
spattern=($(python -c "from config import stable_pattern; print stable_pattern" | tr -d "(),'"))
cbranches=($(python -c "from config import chromeos_branches; print chromeos_branches" | tr -d "(),'"))
cpattern=($(python -c "from config import chromeos_pattern; print chromeos_pattern" | tr -d "(),'"))

# Simple clone:
# Clone repository, do not add 'upstream' remote
clone_simple()
{
    local destdir=$1
    local repository=$2
    local force=$3

    echo "Cloning ${repository} into ${destdir}"

    if [[ -d "${destdir}" ]]; then
	pushd "${destdir}" >/dev/null
	git checkout master
	if [[ -n "${force}" ]]; then
	    # This is needed if the origin may have been rebased
	    git fetch origin
	    git reset --hard origin/master
	else
	    git pull
	fi
	popd >/dev/null
    else
	git clone "${repository}" "${destdir}"
    fi
}

clone_simple "${upstream_path}" "${upstream_repo}"

# Complex clone:
# Clone repository, add 'upstream' remote,
# check out and update list of branches
clone_complex()
{
    local destdir=$1
    local repository=$2
    local pattern=$3
    local branches=("${!4}")

    echo "Cloning ${repository} into ${destdir}"

    if [[ -d "${destdir}" ]]; then
	pushd "${destdir}" >/dev/null
	git reset --hard HEAD
	git fetch origin
	for branch in ${branches[*]}; do
	    branch="$(printf ${pattern} ${branch})"
	    if git rev-parse --verify "${branch}" >/dev/null 2>&1; then
		git checkout "${branch}"
		if ! git pull; then
		    # git pull may fail if the remote repository was rebased.
		    # Pull it the hard way.
		    git reset --hard "origin/${branch}"
		fi
	    else
		git checkout -b "${branch}" "origin/${branch}"
	    fi
	done
	git remote -v | grep upstream || {
		git remote add upstream "${upstream_path}"
	}
	git fetch upstream
	popd >/dev/null
    else
	git clone "${repository}" "${destdir}"
	pushd "${destdir}" >/dev/null
	for branch in ${branches[*]}; do
	    branch="$(printf ${pattern} ${branch})"
	    git checkout -b "${branch}" "origin/${branch}"
	done
	git remote add upstream "${upstream_path}"
	git fetch upstream
	popd >/dev/null
    fi
}

clone_complex "${stable_path}" "${stable_repo}" "${spattern}" sbranches[*]
clone_complex "${chromeos_path}" "${chromeos_repo}" "${cpattern}" cbranches[*]

echo "Initializing databases"
python initdb.py
