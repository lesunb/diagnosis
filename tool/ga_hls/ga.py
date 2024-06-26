import os
import math
import time
import json
import shlex
import random
import datetime
# import statistics
import subprocess

import numpy as np
import matplotlib.pyplot as plt

from copy import deepcopy
# from tqdm import tqdm

import treenode
import individual

from individual import QUANTIFIERS, RELATIONALS, EQUALS, ARITHMETICS, MULDIV, EXP, LOGICALS, NEG, IMP, FUNC

# from anytree import Node
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from scipy.cluster.hierarchy import dendrogram, linkage
# from timeit import default_timer as timer

import matplotlib
# import numpy
# import sys

# import analyse
# from analyse import Smith_Waterman

import defs

CROSSOVER_RATE = 0.95 ## Rate defined by Núnez-Letamendia
MUTATION_RATE = 0.9  ## Rate defined by Núnez-Letamendia
POPULATION_SIZE = 50 #30  ## Must be an EVEN number
# GENE_LENGTH = 32
# MAX_ALLOWABLE_GENERATIONS = 1000 #10 #616 ##Calculated using ALANDER , J. 1992. On optimal population size of genetic algorithms.
# MAX_ALLOWABLE_GENERATIONS = 3 #10 #616 ##Calculated using ALANDER , J. 1992. On optimal population size of genetic algorithms.
# NUMBER_OF_PARAMETERS = 17 ## Number of parameters to be evolved
# CHROMOSOME_LENGTH = GENE_LENGTH * NUMBER_OF_PARAMETERS
CHROMOSOME_TO_PRESERVE = 0 #4            ## Must be an EVEN number
PARENTS_TO_BE_CHOSEN = 10

SW_THRESHOLD = 35
FOLDS = 10

SCALE = 0.5


# defs.FILEPATH = 'ga_hls/prop_ctrl.py'
# defs.FILEPATH2 = 'ga_hls/prop_ctrl1.py'
# defs.FILEPATH = 'ga_hls/property_distance_obs_r2.py'
# defs.FILEPATH2 = 'ga_hls/property_distance_obs_r2.py'

# FILEPATH = 'ga_hls/benchmark/property_01_err_eight.py'
# FILEPATH2 = 'ga_hls/benchmark/property_01_err_eight.py'

def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False

class GA(object):
    """docstring for GA"""
    def __init__(self, init_form, mutations = None, target_sats = 2):
        super(GA, self).__init__()


        # Log the timespaneach one of the tree steps in the approach
        self.checkin_start = {
            'mutation_timestamp': 0.0,
            'tracheck_timestamp': 0.0,
            'diagnosi_timestamp': 0.0
        }
        self.timespan_log = {
            'mutation_timestamp': 0.0,
            'tracheck_timestamp': 0.0,
            'diagnosi_timestamp': 0.0
        }

        self.mutations = None
        self.force_mutation = False
        print(mutations)
        if mutations is not None:
            self.set_mutation_ranges(mutations)
            self.set_force_mutations(True)

        random.seed()
        self.size = POPULATION_SIZE
        self.population = []
        self.now = datetime.datetime.now()
        curr_path = os.getcwd()
        self.init_form = init_form

        self.target_sats = int(target_sats)
        self.target_mutation = False
        self.check_if_target_is_reachable()

        self.init_log(curr_path)
        self.init_population()
        self.s, self.e = self.get_line('ga_hls')
        self.execution_report = {'TOTAL': 0}

        self.SW = Smith_Waterman()
        self.get_max_score()
        self.check_highest_sat(None)
        self.hypots = []
        self.sats = []
        self.unsats = []
        self.unknown = []

        # self.diag = diagnosis.Diagnosis()
        # self.seed = treenode.parse(json.loads('["ForAll",[["s"],["Implies",[["And",[[">",["s",0]],["<",["s",10]]]],["And",[["<",["signal_4(s)",1000]],[">=",["signal_2(s)",-15.27]]]]]]]]'))

        name = self.copy_temp_file(self.path)
        defs.FILEPATH = name
        defs.FILEPATH2= name
        print(f'Runnnig script {defs.FILEPATH} and {defs.FILEPATH2}')
        # print(f'Runnnig script {name}')
        with open('{}/hypot.txt'.format(self.path), 'a') as f:
            f.write(f'\t{defs.FILEPATH}\n')

    def check_if_target_is_reachable(self):
        total_combination = 1
        combination_set = {}
        f = math.factorial
        if self.mutations is None:
            return
        else:
            for i in self.mutations:
                if self.mutations[i][0] == 'float':
                    return
                elif self.mutations[i][0] == 'int':
                    combination_set[i] = self.mutations[i][1][1] - self.mutations[i][1][0] + 1
                else:
                    combination_set[i] = len(self.mutations[i][1])
        # Check if the combinations are greater or equal than the requested satisfied requirements
        for mutation_comb in combination_set:
            print(mutation_comb)
            total_combination = total_combination * combination_set[mutation_comb]
        if self.target_sats > total_combination:
            print('Requested Satisfied requirements unreachable. Changing to all possible combinations')
            print(f'From {self.target_sats} to {total_combination}')
            self.target_sats = total_combination
            self.target_mutation = True
        return

    def check_highest_sat(self, chromosome):
        self.max_score += self.SW.compare(list(self.seed), list(self.seed), 0,0).traceback_score
        self.highest_sat = None
        return
        if chromosome is None:
            self.highest_sat = None
        else:
            if self.highest_sat is None:
                self.highest_sat = chromosome
                self.max_score += self.SW.compare(list(self.seed), list(self.highest_sat), 0,0).traceback_score
            else:
                result_old = self.SW.compare(list(self.seed), list(self.highest_sat), 0,0)
                result_new = self.SW.compare(list(self.seed), list(chromosome), 0,0)
                if result_old < result_new:
                    self.max_score -= result_old.traceback_score
                    self.highest_sat = chromosome
                    self.max_score += result_new.traceback_score

    def get_max_score(self):
        result = self.SW.compare(self.replace_token(list(self.seed)), self.replace_token(list(self.seed)), 0,0)
        self.max_score = result.traceback_score

    def set_force_mutations(self, forced: bool):
        self.force_mutation = forced

    def set_mutation_ranges(self, mutations: dict):
        self.mutations = mutations

    def init_population(self):
        self.population = []
        root = treenode.parse(self.init_form)
        self.seed = root
        terminators = list(set(treenode.get_terminators(root)))
        self.seed_ch = deepcopy(individual.Individual(root, terminators))
        self.seed_ch.show_idx()
        print(f'terminators = {terminators}')
        # print(f'Initial formula: {root}')
        # for i in tqdm(range(0, self.size)):
        self.checkin('mutation_timestamp')
        for i in range(0, self.size):
            print(i)
            chromosome = deepcopy(individual.Individual(root, terminators))
            chromosome.mutations = deepcopy(self.mutations)
            # print(f'chromosome.mutations = {chromosome.mutations}')
            n = random.randrange(len(root))
            if self.force_mutation:
                chromosome.force_mutate(list(self.mutations.keys()), n)
            else:
                chromosome.mutate(1, n)
            # print(f"{i}: chromosome {chromosome} is {'viable' if chromosome.is_viable(self.path) else 'not viable'}")
            # while not chromosome.is_viable(self.path):
            #     chromosome = deepcopy(individual.Individual(root, terminators))
            #     chromosome.mutations = deepcopy(self.mutations)
            #     if self.force_mutation:
            #         chromosome.force_mutate(list(self.mutations.keys()), random.randrange(len(chromosome)))
            #     else:
            #         chromosome.mutate(1, random.randrange(len(chromosome)))
            #     # print(f"{i}: chromosome {chromosome} is {'viable' if chromosome.is_viable(self.path) else 'not viable'}")
            # print((chromosome.arrf_str()))
            # print(str(chromosome))
            self.population.append(deepcopy(chromosome))
        self.checkout('mutation_timestamp')
        # raise Excevzption('')
        print("Population initialized. Size = {}".format(self.size))

    def init_log(self, parent_dir):
        directory = str(self.now)
        self.path = os.path.join(parent_dir, directory)
        self.path = self.path.replace(' ', '_')
        self.path = self.path.replace(':', '_')
        print(self.path)
        try:
            os.mkdir(self.path)
            pass
        except OSError as error:
            print(error)

    def show(self):
        self.evaluate()
        self.population.sort(key=lambda x: x.fitness)
        print(f"Best solution so far have fitness = {self.population[0].fitness}")
        print(f"Best solution has {self.count_distinct_edges(self.population[0])} against all {len(self.graph.edges())} edges")
        print("Best solution = ", self.population[0])
        print("Paths")
        for i in range(self.ncars):
            car = self.population[0].paths[i]
            print('->'.join([str(x.name) for x in car.path]))

    def get_line(self, file):
        # print(f'Running on {os.getcwd()} folder')
        file_path = defs.FILEPATH
        # file_path = f'{self.path}/z3check.py'
        newf_str = ''
        print(f'Running on {file_path} folder')
        with open(file_path) as f:
            f.seek(0, 0)
            for l in f:
                if l.find('z3solver.check') > 0:
                    break
                else:
                    newf_str += l
            # print(f'py file seek at = {len(newf_str)}')
            d1 = newf_str.rfind('\t')
            d2 = newf_str[1:d1-1].rfind('\t')
            # print(f'py file seek at = {d2}')
            self.first = newf_str
            return d2, newf_str.rfind('\n')

    def save_file(self, s, e, nline):
        src = defs.FILEPATH
        # src =  f'{self.path}/z3check.py'
        dst = f'{self.path}/temp.py'
        # print(f'Running on {defs.FILEPATH} folder')
        with open(src) as firstfile, open(dst,'w') as secondfile:
            firstfile.seek(e)
            secondfile.write(self.first[:s])
            secondfile.write('\n\n')
            secondfile.write(f'\tz3solver.add({nline})\n')
            for l in firstfile:
                secondfile.write(l)

    def copy_temp_file(self, folder_path):
        lines = []
        with open(defs.FILEPATH2,'r') as file:
            for l in file:
                lines.append(l)

        filename = defs.FILEPATH2.split('/')[-1]

        with open(f'{folder_path}/{filename}','w') as file:
            for l in lines:
                file.write(l)
        return f'{folder_path}/{filename}'

    def test_chromosome(self, chromosome):
        # print(f'writing test for: {str(chromosome)}')
        def find_traces_in_file(file_path = defs.FILEPATH2):
            print(f'Running on {os.getcwd()} folder')
            print(f'Running on {file_path} folder')
            newf_str1 = ''
            newf_str2 = ''
            with open(file_path) as f:
                for l in f:
                    if l.find('z3solver.check') > 0:
                        break
                    else:
                        newf_str2 += l
                f.seek(0, 0)
                for l in f:
                    if l.find('z3solver.add') > 0:
                        break
                    else:
                        newf_str1 += l
                print(f'py file seek at = {len(newf_str1)}')
                d1 = newf_str2.rfind('\n')
                d2 = newf_str2[1:d1-1].rfind('\t')
                print(f'py file seek at = {d2}')
                self.first = newf_str1
                return newf_str1.rfind('\n'), d2
        def save_z3check(s, e, nline):
            src = defs.FILEPATH2
            file = f'{self.path}/z3check.py'
            print(f'Running on {file} folder')
            form_line = ''
            newf_str2 = ''
            newf_str3 = ''
            with open(file,'r+') as z3check_file:
                for l in z3check_file:
                    if l.find('z3solver.check') > 0:
                        # form_line = l
                        print('found: '+l)
                        break
                    else:
                        newf_str2 += l
                d1 = newf_str2.rfind('\n')
                d2 = newf_str2[1:d1-1].rfind('\n')
            with open(file,'r+') as z3check_file:
                for l in z3check_file:
                    if l.find('z3solver.check') > 0:
                        # form_line = l
                        print('found: '+l)
                        break
                    else:
                        newf_str3 += l
                newf_str2 = newf_str2[1:d2]
                z3check_file.seek(0, 0)
                print(newf_str2)
                z3check_file.write('\n')
                z3check_file.write(newf_str2)
                form_line = (f'\tz3solver.add({nline})\n')
                print(form_line)
                z3check_file.write(form_line)
                z3check_file.write('\n')
                # for l in z3check_file:
                #     z3check_file.write(l)
                # z3check_file.seek(0, 0)
                # firstfile.seek(0, 0)

        def get_file_w_traces(file_path = defs.FILEPATH2):
            s = e = -1
            lines = []
            with open(file_path) as f:
                for l in f:
                    lines.append(l)
            # print('lines')
            for idx, l in enumerate(lines):
                if l.find('z3solver.add') >= 0:
                    # print(idx, l)
                    s = idx
                    break
            for idx, l in enumerate(lines):
                # print(l, l.find('z3solver.check'))
                if l.find('z3solver.check') >= 0:
                    # print(idx, l)
                    e = idx
                    break
            # print('lines')
            return s, e, lines
        
        def save_check_wo_traces(start, end, lines, nline, file_path = 'ga_hls/z3check.py'):
            before = lines[:start]
            after = lines[end:]
            with open(file_path,'w') as z3check_file:
                for l in before:
                    z3check_file.write(l)
                form_line = (f'\tz3solver.add({nline})\n')
                z3check_file.write('\n')
                # print(form_line)
                z3check_file.write(form_line)
                z3check_file.write('\n')
                for l in after:
                    z3check_file.write(l)

        def reset_file(path):
            f = open(path, 'r')
            f.seek(0, 0)
            f.close()

        # s, e = find_traces_in_file()
        # save_z3check(s, e, f'Not({chromosome.format()})')

        new_file = self.copy_temp_file(self.path)
        raise("")
        start, end, lines = get_file_w_traces(new_file)
        save_check_wo_traces(start, end, lines, f'Not({chromosome.format()})', new_file)
        reset_file(defs.FILEPATH2)
        reset_file(new_file)

        # folder_name = 'ga_hls'
        folder_name = self.path
        run_str = f'python3 {folder_name}/z3check.py'
        run_tk = shlex.split(run_str)
        run_process = subprocess.run(run_tk,
                                     stderr=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     universal_newlines=True,
                                     timeout=100)
        # print(run_process.stdout)
        if run_process.stdout.find('SATISFIED') > 0:
            # print('Chromosome not viable')
            return True
        elif run_process.stdout.find('VIOLATED') > 0:
            # print('Chromosome viable')
            return True
        else:
            # print('Chromosome not viable')
            return False
        return

    def get_best(self):
        return self.population[0]

    def write_population(self, generation):
        with open('{}/{:0>2}.txt'.format(self.path, generation), 'w') as f:
            f.write('Formula\tFitness\tSatisfied\n')
            if self.highest_sat:
                f.write('HC: ')
                f.write(str(self.highest_sat))
                f.write(f'\t{self.highest_sat.fitness}')
                f.write(f'\t{self.highest_sat.madeit}')
                f.write('\n')
            for i, chromosome in enumerate(self.population):
                f.write('{:0>2}'.format(i)+': ')
                # print(chromosome.format())
                f.write(str(chromosome))
                f.write(f'\t{chromosome.fitness}')
                f.write(f'\t{chromosome.madeit}')
                f.write('\n')
        json_object = json.dumps(self.execution_report, indent=4)
        with open(f"{self.path}/report.json", "w") as outfile:
            outfile.write(json_object)

    def clusterize(self, generation):
        # this method applies the SW algorithm to all formulas
        results = []
        score_matrix = [[0 for x in range(self.size)] for y in range(self.size)]
        labels = []
        SW = Smith_Waterman()
        for idx, el in enumerate(self.population):
            labels.append('{:0>2}{}'.format(idx,'T' if el.madeit == 'True' else 'F'))
        for i, c1 in enumerate(self.population):
            for j, c2 in zip(range(i+1, self.size), self.population[i+1:]):
                new_result = SW.compare(list(c1), list(c2), i, j)
                score_matrix[j][i] = score_matrix[i][j] = new_result.traceback_score
                results.append(new_result)
        # return list(sorted(results, reverse = True)), score_matrix

        hypot = [float('inf'), '']
        ## write dendrogram
        Z = create_dendrogram('{}/sw_ga_{:0>2}'.format(self.path, generation), score_matrix, labels, inverse_score=True)
        if Z is not None:
            for idx, el in enumerate(self.population):
                if el.madeit == 'True': #and Z[idx-1][2] < 0.0333:
                    print(f'{idx}: {Z[idx-1][2]}: {el}')
                    self.hypots.append([Z[idx-1][2], el])
                    # if hypot[0] > Z[idx-1][2]:
                    #     hypot = [Z[idx-1][2], el]
            # self.hypots.append(hypot)

    def generate_dataset_qty(self):
        res = []
        [res.append(x) for x in self.population if x not in res]
        [self.unknown.append(x) for x in self.population if (x not in self.unknown) and (x.madeit == 'Unknown')]
        [self.unsats.append(x) for x in self.population if (x not in self.unsats) and (x.madeit == 'False')]
        [self.sats.append(x) for x in self.population if (x not in self.sats) and (x.madeit == 'True')]
        print(f'\nWe have so far {len(self.sats)} satisfied')
        print(f'and {len(self.unsats)} unsatisfied')
        print(f'and {len(self.unknown)} unknown')

    def generate_dataset_threshold(self):
        res = []
        [res.append(x) for x in self.population if x not in res]
        [self.unknown.append(x) for x in self.population if (x not in self.unknown) and (x.madeit == 'Unknown')]
        [self.unsats.append(x) for x in self.population if (x not in self.unsats) and (x.madeit == 'False')]
        [self.sats.append(x) for x in self.population if (x not in self.sats) and (x.sw_score > SW_THRESHOLD) and (x.madeit == 'True')]

    def build_attributes(self, formulae: list):
        count_op = {
            'QUANTIFIERS': 0,
            'RELATIONALS': 0,
            'EQUALS': 0,
            'ARITHMETICS': 0,
            'MULDIV': 0,
            'EXP': 0,
            'LOGICALS': 0,
            'FUNC': 0,
            'NEG': 0,
            'IMP': 0,
            'NUM': 0,
            'SINGALS': 0,
            'TERM': 0
        }
        terminators = list(set(treenode.get_terminators(self.seed)))
        terminators = [value for value in terminators if not isinstance(value, int) and not isinstance(value, float)]
        ret = []
        for term in formulae:
            if term in QUANTIFIERS:
                qstring = str(QUANTIFIERS)
                qstring = qstring.replace('\'', '')
                qstring = qstring.replace(']', '}')
                qstring = qstring.replace('[', '{')
                ret.append(f'QUANTIFIERS{count_op["QUANTIFIERS"]} {qstring}')
                count_op['QUANTIFIERS'] = count_op['QUANTIFIERS'] + 1
            elif term in RELATIONALS:
                qstring = str(RELATIONALS)
                qstring = qstring.replace('\'', '')
                qstring = qstring.replace(']', '}')
                qstring = qstring.replace('[', '{')
                ret.append(f'RELATIONALS{count_op["RELATIONALS"]} {qstring}')
                count_op['RELATIONALS'] = count_op['RELATIONALS'] + 1
            elif term in EQUALS:
                qstring = str(EQUALS)
                qstring = qstring.replace('\'', '')
                qstring = qstring.replace(']', '}')
                qstring = qstring.replace('[', '{')
                ret.append(f'EQUALS{count_op["EQUALS"]} {qstring}')
                count_op['EQUALS'] = count_op['EQUALS'] + 1
            elif term in ARITHMETICS:
                qstring = str(ARITHMETICS)
                qstring = qstring.replace('\'', '')
                qstring = qstring.replace(']', '}')
                qstring = qstring.replace('[', '{')
                ret.append(f'ARITHMETICS{count_op["ARITHMETICS"]} {qstring}')
                count_op['ARITHMETICS'] = count_op['ARITHMETICS'] + 1
            elif term in MULDIV:
                qstring = str(MULDIV)
                qstring = qstring.replace('\'', '')
                qstring = qstring.replace(']', '}')
                qstring = qstring.replace('[', '{')
                ret.append(f'MULDIV{count_op["MULDIV"]} {qstring}')
                count_op['MULDIV'] = count_op['MULDIV'] + 1
            elif term in EXP:
                qstring = str(EXP)
                qstring = qstring.replace('\'', '')
                qstring = qstring.replace(']', '}')
                qstring = qstring.replace('[', '{')
                ret.append(f'EXP{count_op["EXP"]} {qstring}')
                count_op['EXP'] = count_op['EXP'] + 1
            elif term in LOGICALS:
                qstring = str(LOGICALS)
                qstring = qstring.replace('\'', '')
                qstring = qstring.replace(']', '}')
                qstring = qstring.replace('[', '{')
                ret.append(f'LOGICALS{count_op["LOGICALS"]} {qstring}')
                count_op['LOGICALS'] = count_op['LOGICALS'] + 1
            elif term in NEG:
                qstring = str(NEG)
                qstring = qstring.replace('\'', '')
                qstring = qstring.replace(']', '}')
                qstring = qstring.replace('[', '{')
                ret.append(f'NEG{count_op["NEG"]} {qstring}')
                count_op['NEG'] = count_op['NEG'] + 1
            elif term in IMP:
                qstring = str(IMP)
                qstring = qstring.replace('\'', '')
                qstring = qstring.replace(']', '}')
                qstring = qstring.replace('[', '{')
                ret.append(f'IMP{count_op["IMP"]} {qstring}')
                count_op['IMP'] = count_op['IMP'] + 1
            elif term in terminators:
                qstring = str(terminators)
                qstring = qstring.replace('\'', '')
                qstring = '{'+qstring[1:-1]+'}'
                ret.append(f'TERM{count_op["TERM"]} {qstring}')
                count_op['TERM'] = count_op['TERM'] + 1
            elif term.isnumeric() or isfloat(term):
                ret.append(f'NUM{count_op["NUM"]} NUMERIC')
                count_op['NUM'] = count_op['NUM'] + 1
            elif term in FUNC:
                qstring = str(FUNC)
                qstring = qstring.replace('\'', '')
                qstring = qstring.replace(']', '}')
                qstring = qstring.replace('[', '{')
                ret.append(f'FUNC{count_op["FUNC"]} {qstring}')
                count_op['FUNC'] = count_op['FUNC'] + 1
        return ret

    def store_dataset_all(self):
        # entire_dataset = self.sats + self.unsats + self.unknown
        entire_dataset = list()
        [self.entire_dataset.append(x) for x in self.unknown if (x not in self.entire_dataset)]
        [self.entire_dataset.append(x) for x in self.unsats if (x not in self.entire_dataset)]
        [self.entire_dataset.append(x) for x in self.sats if (x not in self.entire_dataset)]
        per_cut = 1.0

        try:
            chstr = self.population[0].arrf_str()
        except Exception as e:
            chstr = str(self.seed_ch)

        attrs = self.build_attributes(chstr.split(','))
        # for att in attrs:
        #     print(att)

        nowstr = f'{self.now}'.replace(' ', '_')
        nowstr = nowstr.replace(':', '_')
        filename_str = '{}/dataset_qty_{}_all.arff'.format(self.path, nowstr)
        with open(filename_str, 'w') as f:
            nowstr = f'{nowstr}\n'
            nowstr = nowstr.replace(' ', '_')
            s = f'@relation all.{nowstr}\n'
            f.write(s)
            f.write('\n')
            for att in attrs:
                f.write(f'@attribute {att}\n')

            f.write('@attribute VEREDICT {TRUE, FALSE, UNKNOWN}\n')
            f.write('\n')
            f.write('@data\n')
            for chromosome in entire_dataset:
                # print('writing sats')
                ch_str = chromosome.arrf_str()
                # ch_str = ch_str.replace(' ', ',')
                # ch_str = ch_str.replace(',t,In,(', ',')
                # ch_str = ch_str.replace('),Implies,(', ',Implies,')
                f.write(ch_str)
                f.write(f",{chromosome.madeit.upper()}\n")
        return filename_str

    def store_dataset_qty(self, per_cut: float):
        self.sats.sort(key=lambda x : x.sw_score, reverse=True)
        self.unsats.sort(key=lambda x : x.sw_score, reverse=True)
        self.unknown.sort(key=lambda x : x.sw_score, reverse=True)

        min_len = min([len(self.sats), len(self.unsats), len(self.unknown)])
        per_qty = math.ceil(min_len * per_cut)
        # print(f'per_qty = {per_qty}')
        sats = self.sats
        unsats = self.unsats
        unknown = self.unknown
        if len(sats) > per_qty:
            sats = sats[:per_qty]
        if len(unsats) > per_qty:
            unsats = unsats[:per_qty]
        if len(unknown) > per_qty:
            unknown = unknown[:per_qty]
        # print(f'len sats = {len(sats)}')
        # print(f'len unsats = {len(unsats)}')
        # print(f'len unknown = {len(unknown)}')

        try:
            chstr = sats[0].arrf_str()
        except Exception as e:
            chstr = str(self.seed_ch)

        # print(chstr)
        # chstr = chstr.replace(' ', ',')
        # chstr = chstr.replace(',In,(', ',')
        # chstr = chstr.replace('),Implies,(', ',Implies,')
        # chstr = chstr[:-1]
        # print(chstr)
        # print(sats[0].arrf_str())
        # print(chstr.split(','))
        attrs = self.build_attributes(chstr.split(','))
        # for att in attrs:
        #     print(att)

        nowstr = f'{self.now}'.replace(' ', '_')
        nowstr = nowstr.replace(':', '_')
        filename_str = '{}/dataset_qty_{}_per{:0>3d}.arff'.format(self.path, nowstr, int(per_cut*100))
        with open(filename_str, 'w') as f:
            nowstr = f'{nowstr}\n'
            nowstr = nowstr.replace(' ', '_')
            s = f'@relation all.{nowstr}\n'
            f.write(s)
            f.write('\n')
            for att in attrs:
                f.write(f'@attribute {att}\n')

            f.write('@attribute VEREDICT {TRUE, FALSE, UNKNOWN}\n')
            f.write('\n')
            f.write('@data\n')
            for chromosome in sats:
                # print('writing sats')
                ch_str = chromosome.arrf_str()
                # ch_str = ch_str.replace(' ', ',')
                # ch_str = ch_str.replace(',t,In,(', ',')
                # ch_str = ch_str.replace('),Implies,(', ',Implies,')
                f.write(ch_str)
                f.write(f",{chromosome.madeit.upper()}\n")
            for chromosome in unsats:
                # print('writing unsats')
                ch_str = chromosome.arrf_str()
                # ch_str = ch_str.replace(' ', ',')
                # ch_str = ch_str.replace(',t,In,(', ',')
                # ch_str = ch_str.replace('),Implies,(', ',Implies,')
                f.write(ch_str)
                f.write(f",{chromosome.madeit.upper()}\n")
            for chromosome in unknown:
                # print('writing unsats')
                ch_str = chromosome.arrf_str()
                # ch_str = ch_str.replace(' ', ',')
                # ch_str = ch_str.replace(',t,In,(', ',')
                # ch_str = ch_str.replace('),Implies,(', ',Implies,')
                f.write(ch_str)
                f.write(f",{chromosome.madeit.upper()}\n")
        return filename_str

    def store_dataset_threshold(self):
        self.unsats.sort(key=lambda x : x.sw_score, reverse=True)
        if len(self.unsats) > len(self.sats):
            self.unsats = self.unsats[:len(self.sats)]
        else:
            self.sats = self.sats[:len(self.unsats)]

        with open('{}/dataset_{}.arff'.format(self.path, self.now), 'w') as f:
            f.write('@relation all.generationall\n')
            f.write('\n')
            f.write('@attribute QUANTIFIERS {ForAll, Exists}\n')
            f.write('@attribute VARIABLE {s}\n')
            f.write('@attribute RELATIONALS {<,>,<=,>=, =}\n')
            f.write('@attribute NUMBER NUMERIC\n')
            f.write('@attribute LOGICALS1 {And, Or}\n')
            f.write('@attribute VARIABLE1 {s}\n')
            f.write('@attribute RELATIONALS1 {<,>,<=,>=, =}\n')
            f.write('@attribute NUMBER1 NUMERIC\n')
            f.write('@attribute IMP1 {Implies}\n')
            f.write('@attribute SIGNALS {signal_2(s),signal_4(s)}\n')
            f.write('@attribute RELATIONALS2 {<,>,<=,>=, =}\n')
            f.write('@attribute NUMBER2 NUMERIC\n')
            f.write('@attribute LOGICALS2 {And, Or}\n')
            f.write('@attribute SIGNALS1 {signal_2(s),signal_4(s)}\n')
            f.write('@attribute RELATIONALS3 {<,>,<=,>=, =}\n')
            f.write('@attribute NUMBER3 NUMERIC\n')
            f.write('@attribute VEREDICT {TRUE, FALSE, UNKNOWN}\n')
            f.write('\n')
            f.write('@data\n')
            for chromosome in self.sats:
                ch_str = str(chromosome)
                ch_str = ch_str.replace(' ', ',')
                ch_str = ch_str.replace(',s,In,(', ',')
                ch_str = ch_str.replace('),Implies,(', ',Implies,')
                f.write(ch_str[:-1])
                f.write(f",{chromosome.madeit.upper()}\n")
            for chromosome in self.unsats:
                ch_str = str(chromosome)
                ch_str = ch_str.replace(' ', ',')
                ch_str = ch_str.replace(',s,In,(', ',')
                ch_str = ch_str.replace('),Implies,(', ',Implies,')
                f.write(ch_str[:-1])
                f.write(f",{chromosome.madeit.upper()}\n")

    # def dist2VF(self, generation):
    #     res = []
    #     [res.append(x) for x in self.population if x not in res]
    #     # print(res)
        
    #     sats = []
    #     unsats = []
    #     for chromosome in res:
    #         if chromosome.madeit == False:
    #             unsats.append(chromosome)
    #         else:
    #             sats.append(chromosome)

    #     # print(sats)
    #     # print(unsats)

    #     sats.sort(key=lambda x : x.sw_score, reverse=True)
    #     unsats.sort(key=lambda x : x.sw_score, reverse=True)

    #     per20 = int(POPULATION_SIZE * .20)
    #     if len(sats) > per20:
    #         sats = sats[:per20]
    #     if len(unsats) > per20:
    #         unsats = unsats[:per20]

    #     with open('{}/{:0>2}_pareto.txt'.format(self.path, generation), 'w') as f:
    #         f.write('Formula\tSW_Score\tSatisfied\n')
    #         f.write('SEED: ')
    #         f.write(str(self.seed_ch))
    #         f.write(f'\t-')
    #         f.write(f'\t-')
    #         f.write('\n')
    #         for i, chromosome in enumerate(sats):
    #             f.write('{:0>2}'.format(i)+': ')
    #             f.write(str(chromosome))
    #             f.write(f'\t{chromosome.sw_score}')
    #             f.write(f'\t{chromosome.madeit}')
    #             f.write('\n')
    #         f.write('\n')
    #         f.write('\n')
    #         for i, chromosome in enumerate(unsats):
    #             f.write('{:0>2}'.format(i)+': ')
    #             f.write(str(chromosome))
    #             f.write(f'\t{chromosome.sw_score}')
    #             f.write(f'\t{chromosome.madeit}')
    #             f.write('\n')
    #     json_object = json.dumps(self.execution_report, indent=4)
    #     with open(f"{self.path}/report.json", "w") as outfile:
    #         outfile.write(json_object)

    def pool(self):
        return deepcopy(self.population[random.randint(0, 32767) % PARENTS_TO_BE_CHOSEN])

    def roulette_wheel_selection(self):
        population_fitness = sum([chromosome.fitness for chromosome in self.population])
        if population_fitness == 0:
            chromosome_probabilities = [1/len(self.population) for chromosome in self.population]
        else:
            chromosome_probabilities = [chromosome.fitness/population_fitness for chromosome in self.population]
        
        return deepcopy(np.random.choice(self.population, p=chromosome_probabilities))

    def check_evolution(self):
        if self.target_mutation == True:
            evolved = (len(self.sats)+len(self.unsats)) >= self.target_sats
        else:
            evolved = (len(self.sats) >= self.target_sats) and (len(self.unsats) >= self.target_sats)
        # max_allowed = self.generation_counter < MAX_ALLOWABLE_GENERATIONS
        # print(f"{self.count_distinct_edges(self.population[0])} < {len(self.graph.edges())} = {evolved}")
        return (evolved)

    def checkin(self, logtype: str):
        self.checkin_start[logtype] = time.time()
        print(f'Check in: {logtype} {self.checkin_start[logtype]} seconds')

    def checkout(self, logtype: str):
        self.checkin_start[logtype] = time.time() - self.checkin_start[logtype]
        print(f'Check out: {logtype} {self.checkin_start[logtype]} seconds')
        self.timespan_log[logtype] = self.timespan_log[logtype] + self.checkin_start[logtype]
        print(f'Timespan: {logtype} {self.timespan_log[logtype]} seconds')

    def write_timespan_log(self):
        json_object = json.dumps(self.timespan_log, indent=4)
        with open(f"{self.path}/timespan.json", "w") as outfile:
            outfile.write(json_object)

    def evolve(self):
        with open('{}/hypot.txt'.format(self.path), 'a') as f:
            for hypot in self.hypots:
                f.write(f'\t{hypot[1]}\n')
        # loop
        self.generation_counter = 0
       
        self.generate_dataset_qty()
        s100 = self.store_dataset_all()
        
        self.checkin('tracheck_timestamp')
        self.evaluate()
        self.checkout('tracheck_timestamp')
        
        while not self.check_evolution():
            self.checkin('mutation_timestamp')
        # for i in range(MAX_ALLOWABLE_GENERATIONS):
        # for i in tqdm(range(MAX_ALLOWABLE_GENERATIONS)):

            self.population.sort(key=lambda x: x.fitness, reverse=True)
            self.write_population(self.generation_counter)
            # self.dist2VF(self.generation_counter)
            self.generate_dataset_qty()
            s100 = self.store_dataset_all()

            new_population = self.population[:CHROMOSOME_TO_PRESERVE]

            terminators = list(set(treenode.get_terminators(self.seed)))
            
            population_counter = CHROMOSOME_TO_PRESERVE
            while(population_counter < POPULATION_SIZE):
                offspring1 = self.roulette_wheel_selection()
                offspring2 = self.roulette_wheel_selection()

                self.crossover(offspring1, offspring2)

                if self.force_mutation:
                    offspring1.force_mutate(list(self.mutations.keys()), random.randrange(len(offspring1)))
                else:
                    offspring1.mutate(MUTATION_RATE)

                # while not offspring1.is_viable(self.path):
                #     offspring1 = deepcopy(individual.Individual(self.seed, terminators))
                #     offspring1.mutations = self.mutations
                #     if self.force_mutation:
                #         offspring1.force_mutate(list(self.mutations.keys()), random.randrange(len(offspring1)))
                #     else:
                #         offspring1.mutate(MUTATION_RATE)
                #     # print(f"offspring1 is {'viable' if offspring1.is_viable(self.path) else 'not viable'}")

                if self.force_mutation:
                    offspring2.force_mutate(list(self.mutations.keys()), random.randrange(len(offspring2)))
                else:
                    offspring2.mutate(MUTATION_RATE)
                # while not offspring2.is_viable(self.path):
                #     offspring2 = deepcopy(individual.Individual(self.seed, terminators))
                #     offspring2.mutations = self.mutations
                #     if self.force_mutation:
                #         offspring2.force_mutate(list(self.mutations.keys()), random.randrange(len(offspring2)))
                #     else:
                #         offspring2.mutate(MUTATION_RATE)
                #     # print(f"offspring2 is {'viable' if offspring2.is_viable(self.path) else 'not viable'}")
                new_population.append(offspring1)
                new_population.append(offspring2)

                # Reset fitness 
                offspring1.reset()
                offspring2.reset()

                population_counter += 2
            self.generation_counter += 1
            self.population = new_population
            self.checkout('mutation_timestamp')

            # self.diagnosis()

            # write population before trace checker
            self.generate_dataset_qty()
            s100 = self.store_dataset_all()

            ## score population
            self.checkin('tracheck_timestamp')
            self.evaluate()

            s100 = self.store_dataset_qty(1.0)
            s025 = self.store_dataset_qty(.25)
            s020 = self.store_dataset_qty(.20)
            s015 = self.store_dataset_qty(.15)
            s010 = self.store_dataset_qty(.10)
            self.store_dataset_all()
            self.checkout('tracheck_timestamp')

            self.write_timespan_log()

        self.checkin('diagnosi_timestamp')
        s100 = self.store_dataset_qty(1.0)
        s025 = self.store_dataset_qty(.25)
        s020 = self.store_dataset_qty(.20)
        s015 = self.store_dataset_qty(.15)
        s010 = self.store_dataset_qty(.10)
        self.j48(s100, 1.0)
        self.j48(s025, .25)
        self.j48(s020, .20)
        self.j48(s015, .15)
        self.j48(s010, .10)
        self.checkout('diagnosi_timestamp')
        self.write_timespan_log()


    def replace_token(self, tk_list):
        l = list()
        for tk in tk_list:
            if tk in [">=", "<="]:
                l.append(tk.value[0])
                l.append(tk.value[1])
            else:
                l.append(tk)
        return l

    def diagnosis(self):
        return
        hypots = []
        for hypot in self.hypots:
            hypots.append(list(hypot[1]))

        # if len(hypots) == 0:
        length = len(hypots[0])
        aux = np.array(hypots)
        aux = aux.transpose()
        d = {}
        for i in range(len(aux)):
            d[i] = {}
            # print(list(aux[i]))
            for j in range(len(list(aux[i]))):
                # print(aux[i][j].value)
                val = deepcopy(aux[i][j].value)
                d[i][list(aux[i]).count(val)] = val
        # print(json.dumps(d))
        diag = []
        for pos in d:
            keys = list(d[pos].keys())
            keys.sort(reverse=True)
            diag.append(d[pos][keys[0]])
        print(diag)

    def evaluate(self):
        idx = 0
        for chromosome in self.population:
        # for chromosome in tqdm(self.population):
            print('evaluating ', idx)
            idx = 1+idx
            if chromosome.fitness != -1:
                continue

            # self.test_chromosome(chromosome)
            # print(f'Chromosome {chromosome.format()}')
            # if self.test_chromosome(chromosome) == False:
            #     continue
            # print(f'self.s={self.s}, self.e={self.e}')
            self.save_file(self.s, self.e, f'Not({chromosome.format()})')

            # folder_name = 'ga_hls'
            folder_name = self.path
            run_str = f'python3 {folder_name}/temp.py'
            run_tk = shlex.split(run_str)
            err = ''
            try:
                run_process = subprocess.run(run_tk,
                                             stderr=subprocess.PIPE,
                                             stdout=subprocess.PIPE,
                                             universal_newlines=True,
                                             timeout=60*60)
                # print(f'Not({chromosome.format()})')
                # print(f'Chromosome {chromosome.format()}')
                # print(run_process.stdout)
                # print(run_process.stderr)
                if len(run_process.stderr) > 0:
                    errorn = run_process.stderr.find('Error:')
                    if errorn == -1:
                        errorn = run_process.stderr.find('Exception:')
                    newln = run_process.stderr[:errorn].rfind('\n')
                    err = run_process.stderr[newln+1:-1]
                else:
                    errorn = run_process.stdout.find('REQUIREMENT')
                    err = run_process.stdout[errorn:-1]


                if run_process.stdout.find('SATISFIED') > 0:
                    chromosome.madeit = 'True'
                    # self.check_highest_sat(chromosome)
                elif run_process.stdout.find('VIOLATED') > 0:
                    chromosome.madeit = 'False'
                elif run_process.stdout.find('UNDECIDED') > 0:
                    chromosome.madeit = 'Unknown'
                else:
                    print(run_process.stdout)
                    print(run_process.stderr)
                    chromosome.madeit = 'Problem'
            except subprocess.CalledProcessError as e:
                print("An exception occurred")
                print(e.output)
            except subprocess.TimeoutExpired as e:
                print("Trace checker timed out. Unedcided requirement")
                print(f'Chromosome {chromosome.format()}')
                print(e.output)
                # print(run_process.stdout)
                # print(run_process.stderr)
                chromosome.madeit = 'Unknown'
                err = 'REQUIREMENT UNDECIDED'

            if chromosome.madeit == 'Problem':
                # When we cannot evaluate the chromosome set fitness to zero and evaluate next chromosome
                chromosome.sw_score = 0
                chromosome.fitness = 0
                continue

            if err in self.execution_report.keys():
                self.execution_report[err] += 1
            else:
                self.execution_report[err] = 1
            self.execution_report['TOTAL'] += 1
            
            ## running sw
            new_result = 0
            if self.highest_sat is not None:
                new_result = self.SW.compare(self.replace_token(list(self.highest_sat)), self.replace_token(list(chromosome)), 0,0).traceback_score
            result_seed = self.SW.compare(self.replace_token(list(self.seed)), self.replace_token(list(chromosome)), 0,0).traceback_score
            # print(f'diff = {treenode.compare_tree(self.seed, chromosome.root)}\n')
            chromosome.sw_score = result_seed #+ (treenode.compare_tree(self.seed, chromosome.root) * SCALE)

            # print(f'\n')
            # print(f'{list(self.seed)}')
            # print(f'{list(chromosome)}')
            # print(f'SW score = {self.SW.compare(list(self.seed), list(chromosome), 0,0).traceback_score}')
            # print(f'\n\n')
            # print(f'{list(self.replace_token(self.seed))}')
            # print(f'{list(self.replace_token(chromosome))}')
            # print(f'SW score = {self.SW.compare(self.replace_token(list(self.seed)), self.replace_token(list(chromosome)), 0,0).traceback_score}')
            # print(f'\n')

            chromosome.fitness = int(100 * (result_seed) / self.max_score)# + (treenode.compare_tree(self.seed, chromosome.root) * SCALE)
                # chromosome.madeit = '\n'+run_process.stderr
                # print(run_process.stdout)

    def crossover(self, parent1: individual.Individual, parent2: individual.Individual):
        offsprings = [parent1, parent2]
        # print(f'{offsprings[0]}:\tParent 1 lenght: {len(offsprings[0])} \n{offsprings[1]}:\tParent 2 lenght: {len(offsprings[1])}')
        # if False: # len(offsprings[0]) != len(offsprings[1]):
        #     raise ValueError("Error in crossover: offsprings[0] and offsprings[1] lenght does not match: {} != {}.\n{}\n{}" \
        #         .format(len(offsprings[0].root), len(offsprings[1].root), offsprings[0], offsprings[1]))
        # else:
        cut_idx = random.randint(1, len(offsprings[0])-2) if len(offsprings[0]) < len(offsprings[1]) else random.randint(1, len(offsprings[1])-2)

        try:
            off0_tree, off0_sub, node0 = offsprings[0].root.cut_tree(cut_idx)
            off1_tree, off1_sub, node1 = offsprings[1].root.cut_tree(cut_idx)
        except Exception as e:
            # print(e)
            return offsprings

        node0 += off1_sub
        node1 += off0_sub

        return offsprings

    def j48(self, arff_file, qty):
        # filename_str = '{}/dataset_qty_{}_per{}.arff'.format(self.path, self.now, int(per_cut*100))

        # export CLASSPATH="/home/gabriel/Downloads/weka-3-8-6/weka.jar"
        # java -Xmx1024m weka.classifiers.trees.J48 -t data/breast-cancer.arff -k -d J48-data.model >& J48-data.out
        weka_path='/home/gabriel/Downloads/weka-3-8-6/'
        arff = '\''+arff_file+'\''
        path = '\''+self.path+'\''
        weka = f'java -Xmx1024m weka.classifiers.trees.J48 -t {arff_file} -k -d {self.path}/J48-data-{int(qty*100)}.model' # >& J48-data.out'
        print(weka)
        weka_tk = shlex.split(weka)
        try:
            run_process = subprocess.run(weka_tk,
                                         stderr=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         universal_newlines=True,
                                         timeout=100)
            print(run_process.stdout)
            print(run_process.stderr)
            filename_str = f'{self.path}/J48-data-{int(qty*100)}.out'
            with open(filename_str, 'w') as f:
                f.write(run_process.stdout)
                f.write(run_process.stderr)
        except:
            pass

# this class is used to calculate the Smith-Waterman scores
class Smith_Waterman(object):
    match = None
    mismatch = None
    gap = None

    # default values for the algorithm can be changed when constructing the object
    def __init__ (self, match_score = 3, mismatch_penalty = -3, gap_penalty = -2):
        self.match = match_score
        self.mismatch = mismatch_penalty
        self.gap = gap_penalty

    # main method to compare two sequences with the algorithm
    def compare (self, sequence_1, sequence_2, index1, index2):
        rows = len(sequence_1) + 1
        cols = len(sequence_2) + 1
        # first we calculate the scoring matrix
        scoring_matrix = np.zeros((rows, cols))
        for i, element_1 in zip(range(1, rows), sequence_1):
            for j, element_2 in zip(range(1, cols), sequence_2):
                similarity = self.match if element_1 == element_2 else self.mismatch
                scoring_matrix[i][j] = self._calculate_score(scoring_matrix, similarity, i, j)
        # print(f'\n{scoring_matrix}\n')
        
        # now we find the max value in the matrix
        score = np.amax(scoring_matrix)
        index = np.argmax(scoring_matrix)
        # and decompose its index into x, y coordinates
        x, y = int(index / cols), (index % cols)

        # now we traceback to find the aligned sequences
        # and accumulate the scores of each selected move
        alignment_1, alignment_2 = [], []
        DIAGONAL, LEFT= range(2)
        gap_string = "#GAP#"
        while scoring_matrix[x][y] != 0:
            move = self._select_move(scoring_matrix, x, y)
            
            if move == DIAGONAL:
                x -= 1
                y -= 1
                alignment_1.append(sequence_1[x])
                alignment_2.append(sequence_2[y])
            elif move == LEFT:
                y -= 1
                alignment_1.append(gap_string)
                alignment_2.append(sequence_2[y])
            else: # move == UP
                x -= 1
                alignment_1.append(sequence_1[x])
                alignment_2.append(gap_string)

        # now we reverse the alignments list so they are in regular order
        alignment_1 = list(reversed(alignment_1))
        alignment_2 = list(reversed(alignment_2))

        return SW_Result([alignment_1, alignment_2], score, [sequence_1, sequence_2], [index1, index2])

    # inner method to assist the calculation
    def _calculate_score (self, scoring_matrix, similarity, x, y):
        max_score = 0
        try:
            score = similarity + scoring_matrix[x - 1][y - 1]
            if score > max_score:
                max_score = score                    
        except:
            pass
        try:
            score = self.gap + scoring_matrix[x][y - 1]
            if score > max_score:
                max_score = score
        except:
            pass
        try:
            score = self.gap + scoring_matrix[x - 1][y]
            if score > max_score:
                max_score = score
        except:
            pass
        return max_score

    # inner method to assist the calculation
    def _select_move (self, scoring_matrix, x, y):
        
        scores = []
        try:
            scores.append(scoring_matrix[x-1][y-1])
        except:
            scores.append(-1)
        try:
            scores.append(scoring_matrix[x][y-1])
        except:
            scores.append(-1)
        try:
            scores.append(scoring_matrix[x-1][y])
        except:
            scores.append(-1)

        max_score = max(scores)
        return scores.index(max_score)

# this class contains the results of the SW applied to a pair of CBs
# it's only used to export the results
class SW_Result(object):
    aligned_sequences = None
    traceback_score = None
    elements = None
    indices = None

    def __init__ (self, sequence, score, compared_sequences, indices):
        self.aligned_sequences = sequence
        self.traceback_score = score
        self.elements = compared_sequences
        self.indices = indices

    def __str__ (self):
        out = "Alignment of\n\t" + str(self.indices[0]) +  ": " + str(self.elements[0]) + "\nand\n\t"
        out += str(self.indices[1]) +  ": " +str(self.elements[1]) + ":\n\n\n"

        for sequence in self.aligned_sequences:
            out += "\t" + str(sequence) + "\n"
        out += "\n\tScore: " + str(self.traceback_score)
        
        return out

    def __add__(self, result_2):
        self.traceback_score += result_2.traceback_score
        return self

    def __iadd__(self, result_2):
        return self + result_2

    def __ge__(self, result_2):
        return self.traceback_score >= result_2.traceback_score
    
    def __gt__(self, result_2):
        return self.traceback_score > result_2.traceback_score

    def __le__(self, result_2):
        return self.traceback_score <= result_2.traceback_score

    def __le__(self, result_2):
        return self.traceback_score < result_2.traceback_score

    def __eq__(self, result_2):
        return self.traceback_score == result_2.traceback_score

# this method is used to create the dendrogram that shows which CBs are closer to each other
def create_dendrogram (filename, distance_matrix, labels, inverse_score):
    condensed_matrix = []
    
    matplotlib.rc('xtick', labelsize=20) 
    matplotlib.rc('ytick', labelsize=20) 

    # condenses the distance matrix into one dimension, according if the score needs to be inversed or not
    # that is, if the higher the score the more similar the elements, the score needs to be inversed (i.e., 1/score)
    # so that the most similar elements have a lower score among them
    if inverse_score == True:
        for i in range(len(distance_matrix)):
            for j in range(i+1, len(distance_matrix)):
                if distance_matrix[i][j] == 0:
                    condensed_matrix.append(1.0)
                else:
                    condensed_matrix.append(1.0 / distance_matrix[i][j])

    else:
        for i in range(len(distance_matrix)):
            for j in range(i+1, len(distance_matrix)):
                condensed_matrix.append(distance_matrix[i][j])

    figs = []
    # linkage methods considered
    # methods = ['ward', 'centroid', 'single', 'complete', 'average']
    methods = ['complete']

    # draws one dendrogram for each linkage method
    # and the distance used is:
    #                     |-> 0,                   if c1 = c2
    #  dist (c1, c2) =    |-> 1,                   if SW(c1, c2) = 0
    #                     |-> 1 / SW(c1, c2),      otherwise.
    #
    # if the score inverse_score == True. If inverse_score == False, the distance used is the Levenshtein distance.

    for method in methods:
        Z = linkage(condensed_matrix, method)
        # print(method)
        fig = plt.figure(figsize=(25, 10))
        fig.suptitle(method, fontsize=20, fontweight='bold')
        dn = dendrogram(Z, leaf_font_size=20, labels=labels)
        # if method == 'complete':
        #     # i = 0
        #     for i, l in enumerate(Z):
        #         print(f'{i+1}: {l}')

        #     print(dn)
        figs.append(fig)

    try:
        # exports each dendrogram drawn in a separate page in the pdf
        # pdf = PdfPages(str("dendro_for_" + filename + ".pdf"))
        pdf = PdfPages(str(filename + ".pdf"))
        for fig in figs:
            pdf.savefig(fig)
        pdf.close()
        return Z
    except Exception as e:
        print(e)
        print("ERROR: unable to create output file with dendrogram.")
        # quit()
        return None
