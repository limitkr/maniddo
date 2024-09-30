# -*- coding: utf-8 -*-
"""maniddo.py

마니또
=========
두근두근 나의 마니또는 누구일까~??

* Author: 김용인 (pf 16)
* Email: <limitkr99@gmail.com>

- 정회원과 명예회원 별로 마니또 매칭을 해주는 간단한 프로그램이에요. \n
- 신입 기수와 기존 기수끼리 먼저 매칭이 되도록 설계가 되어있습니다. 기존 기수 인원이 더 많은 경우에는 아쉽지만...기존 기수끼리 매칭이 됩니다.

Requirements :

프로그램 사용하기 전 아래 요구사항에 모두 충족했는지 확인해주세요!

- 프로그램 실행 경로에 `people.csv` 파일이 존재해야 한다.
- `people.csv` 파일에는 **반드시** 3개의 행이 존재해야 한다.
- 3개의 행은 순서대로 '구분', '이름', '기수'를 담아야 한다. 구분(회원 구분)은 `MemberStatus` 을 사용한다.

Usage :

>>> python3 maniddo.py [options]

Options:
    -d,  --debug   디버깅 모드. 문제 없이 마니또 매칭이 이루어지는 확인용 \n
    -h,  --help    도움이 필요하면 저를 불러주세요 \n
"""

from typing import (
    TypedDict,
    Literal,
    Final,
)

from datetime import datetime
from random import shuffle, randint

import sys
import time
import uuid
import logging
import pandas as pd

type MemberStatus = Literal['정회원', '명예회원']
type Generation = Literal['기존기수', '신입기수']
type ShortUUID = str
type Member = TypedDict('Member', {
    'name': str,
    'type': MemberStatus,
    'generation': Generation,
    'id': ShortUUID
})
type Members = list[Member]

# Command line에서 사용 가능한 옵션들
SUPPORTED_OPTIONS: Final = [
    '-d',
    '-h',
]

UNLUCKY_COUNT = 0  # 기존 기수와 매칭된 사람 수
DATA: pd.DataFrame | None = None
MEMBER_ANNOUNCEMENTS: Members = []
ID_LIST: list[str] = []


def main(debug=False):
    global DATA
    time.sleep(0.5)

    print("=====================================")
    print(f"신입 기수는 {get_generation()}기 입니다.")
    print("=====================================")

    DATA = read_file('./people.csv')

    logging.info("정회원 목록 생성중...")
    yb = create_member_list('일반회원', DATA)
    logging.info("완료!")

    logging.info("명예회원 목록 생성중...")
    ob = create_member_list('명예회원', DATA)
    logging.info("완료!")

    # 아이디(uuid) 중복 체크
    # 공지시 사용될 개인별 고유한 아이디로, 절대로 중복 되면 안되기 때문에 체크 필수!!
    # 근데 진~~짜 재수 없으면 중복된 키가 나올 수 있어요..ㅠㅠ 그럴 때는 다시 실행해주시면 돼요
    # 웬만하면 중복 될 일이 없는데 중복된 키가 나온다? 그 날 당장 로또 사세요.
    if is_duplicates(ID_LIST):
        raise ValueError('중복된 키가 발견되어 종료합니다. 다시 실행해주세요.')

    print("정회원 마니또 매칭중...")
    yb_result = match_process(yb, debug=debug, count=True)
    print("완료!")

    print("명예회원 마니또 매칭중...")
    ob_result = match_process(ob, debug=debug, code=False)
    print("완료!\n")

    if debug:
        logging.warning("정회원 마니또 매칭 결과")
        print(yb_result, end="\n\n")

    if debug:
        logging.warning("명예회원 마니또 매칭 결과")
        print(ob_result, end="\n\n")

    logging.warning(f"정회원에서 기존 기수끼리 매칭된 사람 수: {UNLUCKY_COUNT}")

    # 공지용 테이블 만들기
    # 먼저 이름순으로 정렬하고, 이후에 정회원과 명예회원 나눠서 재정렬
    annouce_members: Members = sorted(
        sorted(
            MEMBER_ANNOUNCEMENTS,
            key=lambda x: x['name']
        ),
        key=lambda x: x['type'],
        reverse=True
    )

    annouce_table = pd.DataFrame(columns=['name', 'code'])

    for m in annouce_members:
        annouce_table.loc[len(annouce_table)] = [m['name'], m['id']]

    if debug:
        print(annouce_table)
        return

    logging.warning("\noutput.xlsx 파일을 부원들에게 캡쳐해서 공지방에 공유해주세요!")
    # 메시지 전송용 액셀 파일
    to_excel(yb_result, 'yb_result.xlsx', ['이름', '코드', '메시지', 'debug'])
    to_excel(ob_result, 'ob_result.xlsx', ['이름', '코드', '메시지', 'debug'])

    # 단톡방 공지용 엑셀 파일
    to_excel(annouce_table, 'output.xlsx', ['이름', '코드'])


def to_excel(df: pd.DataFrame, path: str, header: list[str]) -> None:
    df.to_excel(path, index=False, na_rep='N/A', header=header, index_label='ID')
    return


def read_file(filepath: str) -> pd.DataFrame | None:
    try:
        logging.info("csv 파일 읽는중...")
        df = pd.read_csv(filepath, names=['type', 'name', 'generation'])
        logging.info("완료!")
    except FileNotFoundError:
        # 파일을 찾을 수 없는 경우 프로그램 종료
        # 실행되는 위치에 `people.csv` 파일이 존재해야 한다.
        logging.critical("파일을 찾을 수 없습니다.")
        return
    return df


def generate_random_id(length: int = 4) -> ShortUUID:
    """
        알파벳 대문자와 숫자로 이루어진 무작위 문자열을 생성한다.

        :param length: 무작위 ID 길이 (기본: 4)
        :return: 생성된 랜덤 문자열
    """
    return str(uuid.uuid4()).upper().replace('-', '')[:length]


def is_duplicates(id_list: list[str]) -> bool:
    if len(id_list) != len(set(id_list)):
        return True
    return False


def match_process(
        shuffled_members: Members,
        count=False,
        debug=False,
        code=True,
) -> pd.DataFrame:
    """
        랜덤으로 정렬된 회원 리스트를 사용하여 마니또 매칭 결과를 데이터프레임으로 반환한다.
        :param shuffled_members: 랜덤으로 정렬된 회원 리스트
        :param count: 기존 기수와 매칭된 사람 수를 샐지 여부
        :param debug: `True`인 경우 `DataFrame`에 매칭 결과를 상세히 표시
        :param code: `False`인 경우 마니또 코드 대신 이름을 표기
        :return: 마니또 매칭된 데이터프레임
    """
    global UNLUCKY_COUNT
    df = pd.DataFrame(columns=['from', 'to', 'messages', 'debug'])

    for i in range(len(shuffled_members)):
        curr = shuffled_members[i]
        to: Member | None = None
        try:
            to = shuffled_members[i + 1]
        except IndexError:  # 마지막에 정렬된 사람은 가장 첫번째 사람과 매칭
            to = shuffled_members[0]
        finally:
            target = f'{to['id']} ({to['name']})' if debug else to['id']
            maniddo_message = f'{curr['name']}님의 마니또는 {to['id']} 입니다.' if code \
                else f'{curr['name']}님의 마니또는 {to['name']} 입니다.'
            debug_message = f'{curr['generation'][:2]} -> {to['generation'][:2]}' if debug else ""
            df.loc[len(df)] = \
                [
                    curr['name'],
                    target,
                    maniddo_message,
                    debug_message,
                ]
            if count and curr['generation'] == '기존기수' and to['generation'] == '기존기수':
                UNLUCKY_COUNT += 1
    if debug:
        return df
    return df.sample(frac=1).reset_index(drop=True)


def create_member_list(member_type: MemberStatus, csv_data: pd.DataFrame) -> Members:
    old_members: Members = []
    new_members: Members = []
    curr_generation: int = get_generation()
    curr_generation = 17

    for idx, row in csv_data.iterrows():
        if row['type'] != member_type:
            continue

        random_id = generate_random_id()
        ID_LIST.append(random_id)

        temp: Member = {
            'name': row['name'],
            'type': row['type'],
            'id': generate_random_id(),
            'generation': '신입기수' if row['generation'] == curr_generation else '기존기수'
        }
        if row['generation'] == curr_generation:
            new_members.append(temp)
        else:
            old_members.append(temp)
        MEMBER_ANNOUNCEMENTS.append(temp)

    if len(old_members) == 0 and len(new_members) == 0:
        raise ValueError("CSV 파일을 읽는 과정에서 오류가 발생했습니다. csv파일이 요구사항을 충족했나요?")

    if member_type == '일반회원':
        print(f"\t기존 기수는 총 {len(old_members)}명")
        print(f"\t신입 기수는 총 {len(new_members)}명")
    else:
        print(f"\t명예 회원은 총 {len(old_members)}명")

    shuffle(old_members)
    shuffle(new_members)

    return merge_members(old_members, new_members)


def get_generation() -> int:
    """ 현재 날짜를 기준으로 기수를 계산한다. 신입기수 여부 파악용 """
    since: Final = 2016  # 피포의 역사는 2016년 부터 시작
    today = datetime.today()
    base_diff = (today.year - since) * 2

    # 기수 계산은 편의상 1월부터 6월, 7월부터 12월 이렇게 나누었습니다.
    # 예를 들어서, 24년 1월에 이 프로그램을 실행하면 `base_diff`의 값은 16이 되고,
    # 아래 조건문에 따라 `sep` 값은 1이 되기 때문에 해당 날짜의 기수는 17로 계산이 됩니다.
    # 즉, 신입 기수는 17기 입니다.
    if 1 <= today.month <= 6:
        sep = 1
    else:
        sep = 2
    return base_diff + sep


def merge_members(l1: Members, l2: Members) -> Members:
    """ 랜덤으로 섞인 기존 기수 인원과 신입 기수의 인원을 번걸아가면서 병합 """
    merged: Members = []
    min_length = min(len(l1), len(l2))

    for i in range(min_length):
        merged.append(l1[i])
        merged.append(l2[i])

    # 이전 알고리즘
    """
    if len(l1) > min_length:
        merged.extend(l1[min_length:])
    else:
        merged.extend(l2[min_length:])
    """

    # 새로운 알고리즘
    diff = min(abs(len(l1) - len(l2)), abs(len(l2) - len(l1)))
    for i in range(min_length, min_length + diff):
        merged.insert(randint(0, len(merged)), l1[i] if len(l1) > min_length else l2[i])

    return merged


if __name__ == '__main__':
    default_options = {
        'debug': False,
    }
    options = sys.argv[1:]

    for opt in options:
        if opt not in SUPPORTED_OPTIONS:
            raise ValueError('지원하지 않는 옵션입니다.')
        elif opt == '-d':
            default_options['debug'] = True
        elif opt == '-h':
            print("먼저, 프로그램 실행 경로에 `people.csv` 파일이 준비되었는지 확인해주세요.")

    main(debug=default_options['debug'])
