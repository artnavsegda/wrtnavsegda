#!/bin/bash
OPENWRT_DIR=openwrt-15_05
TARGET=r2-15

if [ ! -f "./version" ]; then
    echo "5000" > ./version
fi

VER=$(cat ./version)
echo $(($VER + 1)) > ./version

if [ ! -d $OPENWRT_DIR ]; then
	git clone git://su.radiofid.ru/openwrt-15_05.git
	cd ${OPENWRT_DIR}
	git checkout master
	cd ../
else
	cd ${OPENWRT_DIR}
	git pull
	cd ../
fi

if [ ! -e ${OPENWRT_DIR}/env ]; then
	cd ${OPENWRT_DIR}
	git clone git://su.radiofid.ru/openwrt-envs.git
	mv openwrt-envs env
	cd ../
fi

cd ${OPENWRT_DIR}

./scripts/env switch ${TARGET}

./scripts/feeds uninstall -a
./scripts/feeds update -a
./scripts/feeds install -a
./scripts/feeds uninstall sqm-scripts

./scripts/env switch ${TARGET}

yes "" | make oldconfig

make clean
rm -rf bin/kirkwood/packages/irz/

MAJOR=0
MINOR=1

COMMIT_OPENWRT=`git show --pretty=oneline|head -c 40; cd`
BUILDN_OPENWRT=`git log --pretty=format:'' | wc -l`
BRANCH_OPENWRT=`git branch|grep '*'|cut -d ' ' -f 2`

COMMIT_FEEDS=`cd feeds/irz;git show --pretty=oneline|head -c 40; cd ../../`
BUILDN_FEEDS=`cd feeds/irz;git log --pretty=format:'' | wc -l; cd ../../`
BRANCH_FEEDS=`cd feeds/irz;git branch|grep '*'|cut -d ' ' -f 2; cd ../../`

COMMIT_ENV=`cd env;git show --pretty=oneline|head -c 40; cd ../`
BUILDN_ENV=`cd env;git log --pretty=format:'' | wc -l; cd ../`
BRANCH_ENV=`cd env;git branch|grep '*'|cut -d ' ' -f 2; cd ../`

BDATE=`date +%F`
BTIME=`date +%T`

[ -d files/etc ] || mkdir -p files/etc

F=files/etc/version
MODEL=${TARGET}

echo "MAJOR=$MAJOR" > $F


F=files/etc/version
MODEL=${TARGET}
echo "MAJOR=$MAJOR" > $F
echo "MINOR=$MINOR" >> $F
echo "BUILD=$VER" >> $F
echo "COMMIT_OPENWRT=$COMMIT_OPENWRT" >> $F
echo "BUILD_OPENWRT=$BUILDN_OPENWRT" >> $F
echo "BRANCH_OPENWRT=$BRANCH_OPENWRT" >> $F
echo "COMMIT_FEEDS=$COMMIT_FEEDS" >> $F
echo "BUILD_FEEDS=$BUILDN_FEEDS" >> $F
echo "BRANCH_FEEDS=$BRANCH_FEEDS" >> $F
echo "COMMIT_ENV=$COMMIT_ENV" >> $F
echo "BUILD_ENV=$BUILDN_ENV" >> $F
echo "BRANCH_ENV=$BRANCH_ENV" >> $F
echo "MODEL=$MODEL" >> $F
echo "DATE=$BDATE" >> $F
echo "TIME=$BTIME" >> $F

make -j3

if [ "$?" != "0" ]; then 
   make V=s
fi

cd ../

notify-send "Finish build $TARGET BUILD=$VER"
