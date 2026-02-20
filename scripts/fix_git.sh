#!/bin/bash
cd /repo
git stash
git pull origin main
echo "DONE: git stash + pull"
