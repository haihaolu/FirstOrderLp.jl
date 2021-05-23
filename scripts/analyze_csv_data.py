# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#  This script generates all the experimental results used in the paper.

import os
import numpy as np
import scipy.stats
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams.update({'figure.max_open_warning': 0})

# directory where the csv files are located
CSV_DIR = './csv'

# directory where all the figure pdf and table tex files are written to:
OUTPUT_DIR = './results'
FIGS_DIR = os.path.join(OUTPUT_DIR, 'figs')
TEX_DIR = os.path.join(OUTPUT_DIR, 'tex')

OPT = 'TERMINATION_REASON_OPTIMAL'
KKT_PASSES_LIMIT = 1e5
TIME_LIMIT_SECS = 60 * 60  # 1hr
# shift to use for shifted geometric mean
SGM_SHIFT = int(10)
# penalised average runtime:
PAR = 1.  # can be None, which removes unsolved instead of penalizing

SCALING_EXPS_TO_USE = [
    'off,off',
    'off,pock_chambolle alpha=1',
    '10 rounds,off',
    '10 rounds,pock_chambolle alpha=1',
]

PRIMALWEIGHT_EXPS_TO_USE = [
    'adaptive',
    'Fixed 1e-0',
]

# placeholder:
_BEST_STR = '_best_str_'


# Horrible HACK, but needs to be done
def label_lookup(label):
    if 'pdhg_enhanced' in label:
        return 'PDLP'
    if 'mirror-prox' in label:
        return 'Mirror Prox'
    if 'pdhg_vanilla' in label:
        return 'Vanilla PDHG'
    if 'scs-indirect' in label:
        return 'SCS Indirect'
    if 'scs-direct' in label:
        return 'SCS Direct'
    if 'nopresolve' in label:
        return 'No presolve'
    if 'no restarts' in label:
        return 'No restart'
    if 'adaptive theoretical' in label:
        return 'Adaptive restart (theory)'
    if 'adaptive enhanced' in label:
        return 'PDLP'
    if 'pdhg' in label and 'pdhg_mp_1h' in label:
        return 'PDLP'
    if 'off,off' in label:
        return 'No scaling'
    if 'off,pock_chambolle alpha=1' in label:
        return 'Pock-Chambolle'
    if '10 rounds,off' in label:
        return 'Ruiz'
    if '10 rounds,pock_chambolle alpha=1' in label:
        return 'Ruiz + Pock-Chambolle'
    if 'stepsize' in label:
        if 'adaptive' in label:
            return 'PDLP'
        if 'fixed' in label:
            return 'Fixed step-size'
    if 'primalweight' in label:
        if 'adaptive' in label:
            return 'PDLP'
        if 'Fixed 1e-0' in label:
            return r'Fixed primal weight ($\theta=0$)'
        if _BEST_STR in label:
            return 'Best per-instance fixed primal weight'
    if 'improvements' in label:
        if 'vanilla' in label:
            return 'PDHG'
        st = ''
        if 'restarts' in label:
            st = '+ restarts'
        if 'scaling' in label:
            st = '+ scaling'
        if 'primal weight' in label:
            st = '+ primal weight'
        if 'step size' in label:
            st = '+ step-size'
        return st
    if 'malitskypock' in label:
        if _BEST_STR in label:
            return 'Best per-instance Malitsky-Pock settings'
        return 'Best fixed Malitsky-Pock setting'
    return label


def sanitize_title(title):
    return title.replace('_', ' ').title()


def solved_problems_vs_xaxis_figs(
        dfs,
        xaxis,
        xlabel,
        prefix,
        outer_legend=False):
    plt.figure()
    for k, df_k in dfs.items():
        stats_df = df_k.groupby(xaxis)[xaxis] \
            .agg('count') \
            .pipe(pd.DataFrame) \
            .rename(columns={xaxis: 'frequency'})

        stats_df['cum_solved_count'] = stats_df['frequency'].cumsum()
        stats_df = stats_df.drop(columns='frequency').reset_index()
        plt.plot(stats_df[xaxis],
                 stats_df['cum_solved_count'],
                 label=label_lookup(k))

    plt.ylabel('Number of problems solved')
    plt.xlabel(xlabel)
    plt.title(sanitize_title(prefix))
    if outer_legend:
        plt.legend(bbox_to_anchor=(1.04, 0.5), loc='center left')
    else:
        plt.legend(loc='best')
    path = os.path.join(FIGS_DIR, f'{prefix}_{xaxis}_v_solved_probs.pdf')
    plt.savefig(
        path,
        bbox_inches="tight")


def gen_solved_problems_plots(df, prefix, outer_legend=False):
    exps = df['experiment_label'].unique()
    dfs = {k: df[df['experiment_label'] == k] for k in exps}
    optimal_dfs = {k: v[v['termination_reason'] == OPT]
                   for (k, v) in dfs.items()}

    solved_problems_vs_xaxis_figs(
        optimal_dfs,
        'cumulative_kkt_matrix_passes',
        'Cumulative KKT matrix passes',
        prefix,
        outer_legend)
    solved_problems_vs_xaxis_figs(
        optimal_dfs,
        'solve_time_sec',
        'Wall-clock time (secs)',
        prefix,
        outer_legend)


def gen_solved_problems_plots_split_tol(df, prefix, outer_legend=False):
    tols = df['tolerance'].unique()
    for t in tols:
        gen_solved_problems_plots(
            df[df['tolerance'] == t], prefix + f'_tol_{t:.0E}', outer_legend)


def shifted_geomean(x, shift):
    x = x[~np.isnan(x)]
    # return scipy.stats.mstats.gmean(x)
    sgm = np.exp(np.sum(np.log(x + shift) / len(x))) - shift
    return sgm if sgm > 0 else np.nan


def gen_total_solved_problems_table(df, prefix, par):
    solved_probs = df[df['termination_reason'] == OPT] \
        .groupby('experiment_label')['experiment_label'] \
        .agg('count') \
        .pipe(pd.DataFrame) \
        .rename(columns={'experiment_label': 'Solved count'})
    solved_probs.index.name = 'Experiment'
    solved_probs = solved_probs.reset_index()

    shift = SGM_SHIFT
    kkt_sgm = df.copy()
    if par is not None:
        kkt_sgm.loc[kkt_sgm['termination_reason'] != OPT,
                    'cumulative_kkt_matrix_passes'] = par * KKT_PASSES_LIMIT
    else:
        kkt_sgm.loc[kkt_sgm['termination_reason'] !=
                    OPT, 'cumulative_kkt_matrix_passes'] = np.nan

    # Hack for SCS direct
    kkt_sgm.loc[kkt_sgm['experiment_label'].str.contains(
        'scs-direct'), 'cumulative_kkt_matrix_passes'] = np.nan

    kkt_sgm = kkt_sgm.groupby('experiment_label')['cumulative_kkt_matrix_passes'] \
        .agg(lambda _: shifted_geomean(_, shift)) \
        .pipe(pd.DataFrame) \
        .rename(columns={'cumulative_kkt_matrix_passes':
                         f'KKT passes SGM{shift}'})
    kkt_sgm.index.name = 'Experiment'
    kkt_sgm = kkt_sgm.reset_index()

    wall_clock = df.copy()
    if par is not None:
        wall_clock.loc[wall_clock['termination_reason'] !=
                       OPT, 'solve_time_sec'] = par * TIME_LIMIT_SECS
    else:
        wall_clock.loc[wall_clock['termination_reason']
                       != OPT, 'solve_time_sec'] = np.nan

    wall_clock = wall_clock.groupby('experiment_label')['solve_time_sec'] \
        .agg(lambda _: shifted_geomean(_, shift)) \
        .pipe(pd.DataFrame) \
        .rename(columns={'solve_time_sec': f'Solve time secs SGM10'})
    wall_clock.index.name = 'Experiment'
    wall_clock = wall_clock.reset_index()

    output = solved_probs.merge(kkt_sgm).merge(wall_clock)
    # rename the labels
    for e in output['Experiment']:
        output.loc[output['Experiment'] == e, 'Experiment'] = label_lookup(e)

    table = output.to_latex(
        float_format="%.1f",
        longtable=False,
        index=False,
        caption=f'Performance statistics: {sanitize_title(prefix)}',
        label=f't:solved-probs',
        column_format='lccc',
        escape=False)
    path = os.path.join(TEX_DIR, f'{prefix}_solved_probs_table.tex')
    with open(path, "w") as f:
        f.write(table)
    return output


def gen_total_solved_problems_table_split_tol(df, prefix, par):
    outputs = {}
    tols = df['tolerance'].unique()
    for t in tols:
        outputs[t] = gen_total_solved_problems_table(
            df[df['tolerance'] == t], prefix + f'_tol_{t:.0E}', par)
    return outputs


def plot_loghist(x, nbins):
    x = x[~np.isnan(x)]
    hist, bins = np.histogram(x, bins=nbins)
    logbins = np.logspace(np.log10(bins[0] + 1e-6), np.log10(bins[-1]), nbins)
    plt.hist(x, bins=logbins)
    plt.xscale('log')


def gen_ratio_histograms_split_tol(df, prefix, par):
    tols = df['tolerance'].unique()
    for t in tols:
        gen_ratio_histograms(df[df['tolerance'] == t],
                             prefix + f'_tol_{t:.0E}', par)


def gen_ratio_histograms(df, prefix, par):
    assert len(df['experiment_label'].unique()) == 2

    (l0, l1) = df['experiment_label'].unique()

    def performance_ratio_fn(df, par):
        df = df.reset_index()
        assert len(df) <= 2

        df0 = df[df['experiment_label'] == l0]
        df1 = df[df['experiment_label'] == l1]

        instance = df.instance_name.unique()

        if len(df0) == 1 and df0['termination_reason'].iloc[0] == OPT:
            kkt_passes_0 = df0['cumulative_kkt_matrix_passes'].iloc[0]
        else:
            kkt_passes_0 = par * KKT_PASSES_LIMIT
            if len(df0) == 0:
                print(f'{l0} missing {instance}')

        if len(df1) == 1 and df1['termination_reason'].iloc[0] == OPT:
            kkt_passes_1 = df1['cumulative_kkt_matrix_passes'].iloc[0]
        else:
            kkt_passes_1 = par * KKT_PASSES_LIMIT
            if len(df1) == 0:
                print(f'{l1} missing {instance}')

        # if (df['termination_reason'] != OPT).any():
        #    return np.nan
        return (kkt_passes_0 / kkt_passes_1)

    ratios = df.groupby(['instance_name']) \
        .apply(lambda _: performance_ratio_fn(_, par)) \
        .reset_index(name='ratio')
    plt.figure()
    plt.title(f'({label_lookup(l0)}):({label_lookup(l1)})')
    plot_loghist(ratios['ratio'], 25)
    path = os.path.join(FIGS_DIR, f'{prefix}_performance_ratio.pdf')
    plt.savefig(path)
    table = ratios.to_latex(float_format="%.2f",
                            longtable=False,
                            index=False,
                            caption=f'Performance ratio.',
                            label=f't:solved-probs',
                            column_format='lc')
    path = os.path.join(TEX_DIR, f'{prefix}_({label_lookup(l0)}):'
                                 f'({label_lookup(l1)})_ratio_table.tex')
    with open(path, "w") as f:
        f.write(table)
    shift = 0.
    gmean = shifted_geomean(ratios['ratio'], shift)

# Unsolved problems might be missing from csv, make sure all are accounted for
def fill_in_missing_problems(df, instances_list):
    new_index = pd.Index(instances_list, name='instance_name')
    experiments = df['experiment_label'].unique()
    dfs = []
    for e in experiments:
        old_df = df[df['experiment_label'] == e]
        tol = old_df['tolerance'].unique()[0]
        new_df = old_df.set_index('instance_name').reindex(
            new_index).reset_index()
        # otherwise these would be nan
        new_df['tolerance'] = tol
        new_df['experiment_label'] = e
        dfs.append(new_df)
    return pd.concat(dfs)


# First, make output directories
if not os.path.exists(FIGS_DIR):
    os.makedirs(FIGS_DIR)
if not os.path.exists(TEX_DIR):
    os.makedirs(TEX_DIR)

# Get clean list of all problems we tested on:
with open('../benchmarking/miplib2017_instance_list') as f:
    miplib_instances = f.readlines()
miplib_instances = [p.strip() for p in miplib_instances if p[0] != '#']

with open('../benchmarking/mittelmann_instance_list') as f:
    mittelmann_instances = f.readlines()
mittelmann_instances = [p.strip() for p in mittelmann_instances if p[0] != '#']

# Pull out 'default' (ie best) pdhg implementation to compare against:
df_default = pd.read_csv(
    os.path.join(
        CSV_DIR,
        'miplib_pdhg_enhanced_100k.csv'))
df_default = fill_in_missing_problems(df_default, miplib_instances)

######################################################################

# bisco pdhg vs vanilla pdhg (JOIN DEFAULT)
df = pd.read_csv(os.path.join(CSV_DIR, 'miplib_pdhg_vanilla_100k.csv'))
df = fill_in_missing_problems(df, miplib_instances)
df = pd.concat((df_default, df))
gen_solved_problems_plots_split_tol(df, 'miplib_PDLP_v_vanilla')
gen_total_solved_problems_table_split_tol(df, 'miplib_PDLP_v_vanilla', PAR)
gen_ratio_histograms_split_tol(df, 'miplib_PDLP_v_vanilla', PAR)

######################################################################

# bisco pdhg vs malitsky-pock results (JOIN DEFAULT)
df = pd.read_csv(os.path.join(CSV_DIR, 'miplib_malitskypock_100k.csv'))
mp_solved = df[df['termination_reason'] == OPT] \
            .groupby(['experiment_label', 'tolerance']) \
            ['experiment_label'] \
            .agg('count') \
            .pipe(pd.DataFrame) \
            .rename(columns={'experiment_label': 'solved'}) \
            .reset_index()
dfs = []
for t in df['tolerance'].unique():
    _df = mp_solved[mp_solved['tolerance'] == t]
    best_mp_run = _df.loc[_df['solved'].idxmax()]['experiment_label']
    dfs.append(df[df['experiment_label'] == best_mp_run])
df_best_ind = fill_in_missing_problems(pd.concat(dfs), miplib_instances)

# Pull out best performing fixed weight for each instance / tolerance:
df_best_fixed = df[df['termination_reason'] == OPT].reset_index()
best_idxs = df_best_fixed.groupby(['instance_name', 'tolerance'])['cumulative_kkt_matrix_passes'].idxmin()
df_best_fixed = df_best_fixed.loc[best_idxs]

for t in df_best_fixed['tolerance'].unique():
    # rename the experiment label
    df_best_fixed.loc[df_best_fixed['tolerance'] == t, 'experiment_label'] = \
        f'malitskypock {_BEST_STR} {t}'

df_best_fixed = fill_in_missing_problems(df_best_fixed, miplib_instances)
df_stepsize = pd.read_csv(os.path.join(CSV_DIR, 'miplib_stepsize_100k.csv'))
df_stepsize = fill_in_missing_problems(df_stepsize, miplib_instances)

df = pd.concat((df_stepsize, df_best_fixed, df_best_ind))
gen_solved_problems_plots_split_tol(df, 'miplib_malitskypock')
gen_total_solved_problems_table_split_tol(df, 'miplib_malitskypock', PAR)

######################################################################

# bisco vs mp vs scs on MIPLIB (JOIN PDHG/MP WITH SCS)
df_pdhg_mp = pd.read_csv(os.path.join(CSV_DIR, 'miplib_pdhg_mp_1h.csv'))
df_pdhg_mp = fill_in_missing_problems(df_pdhg_mp, miplib_instances)
df_scs = pd.read_csv(os.path.join(CSV_DIR, 'miplib_scs_1h.csv'))
df_scs = fill_in_missing_problems(df_scs, miplib_instances)
df = pd.concat((df_pdhg_mp, df_scs))
gen_solved_problems_plots_split_tol(df, 'miplib')
gen_total_solved_problems_table_split_tol(df, 'miplib', PAR)

######################################################################

# bisco vs mp vs scs on MITTELMANN (JOIN PDHG/MP WITH SCS)
df_pdhg_mp = pd.read_csv(os.path.join(CSV_DIR, 'mittelmann_pdhg_mp_1h.csv'))
df_pdhg_mp = fill_in_missing_problems(df_pdhg_mp, mittelmann_instances)
df_scs = pd.read_csv(os.path.join(CSV_DIR, 'mittelmann_scs_1h.csv'))
df_scs = fill_in_missing_problems(df_scs, mittelmann_instances)
df = pd.concat((df_pdhg_mp, df_scs))
gen_solved_problems_plots_split_tol(df, 'mittelmann')
gen_total_solved_problems_table_split_tol(df, 'mittelmann', PAR)

######################################################################

# bisco presolve vs no presolve (JOIN DEFAULT)
df = pd.read_csv(os.path.join(CSV_DIR, 'miplib_nopresolve_100k.csv'))
df = pd.concat((df_default, df))
gen_solved_problems_plots_split_tol(df, 'miplib_presolve')
gen_total_solved_problems_table_split_tol(df, 'miplib_presolve', PAR)

######################################################################

# bisco scaling vs no scaling (NO JOIN DEFAULT)
df = pd.read_csv(os.path.join(CSV_DIR, 'miplib_scaling_100k.csv'))
df = fill_in_missing_problems(df, miplib_instances)
# filter out un-needed scaling experiments:
df = pd.concat(df[df['experiment_label'].str.contains(e)]
               for e in SCALING_EXPS_TO_USE)
gen_solved_problems_plots_split_tol(df, 'miplib_scaling')
gen_total_solved_problems_table_split_tol(df, 'miplib_scaling', PAR)

######################################################################

# bisco restart vs no restart (NO JOIN DEFAULT)
df = pd.read_csv(os.path.join(CSV_DIR, 'miplib_restarts_100k.csv'))
df = fill_in_missing_problems(df, miplib_instances)
gen_solved_problems_plots_split_tol(df, 'miplib_restarts')
gen_total_solved_problems_table_split_tol(df, 'miplib_restarts', PAR)

######################################################################

# bisco adaptive stepsize vs fixed stepsize (NO JOIN DEFAULT)
#df = pd.read_csv(os.path.join(CSV_DIR, 'miplib_stepsize_100k.csv'))
#df = fill_in_missing_problems(df, miplib_instances)
#gen_solved_problems_plots_split_tol(df, 'miplib_stepsize')
#gen_total_solved_problems_table_split_tol(df, 'miplib_stepsize', PAR)

######################################################################

# bisco primalweight (NO JOIN DEFAULT)
df = pd.read_csv(os.path.join(CSV_DIR, 'miplib_primalweight_100k.csv'))
df = fill_in_missing_problems(df, miplib_instances)

df_fixed = df[df['experiment_label'].str.contains('Fixed')]

# Pull out best performing fixed weight for each instance / tolerance:
df_best_fixed = df_fixed[df_fixed['termination_reason'] == OPT].reset_index()
best_idxs = df_best_fixed.groupby(['instance_name', 'tolerance'])[
    'cumulative_kkt_matrix_passes'].idxmin()
df_best_fixed = df_best_fixed.loc[best_idxs]

for t in df_best_fixed['tolerance'].unique():
    # rename the experiment label
    df_best_fixed.loc[df_best_fixed['tolerance'] == t, 'experiment_label'] = \
        f'primalweight {_BEST_STR} {t}'

df_best_fixed = fill_in_missing_problems(df_best_fixed, miplib_instances)
df = pd.concat(df[df['experiment_label'].str.contains(e)]
               for e in PRIMALWEIGHT_EXPS_TO_USE)
df = pd.concat((df, df_best_fixed))
gen_solved_problems_plots_split_tol(df, 'miplib_primalweight')
gen_total_solved_problems_table_split_tol(df, 'miplib_primalweight', PAR)


######################################################################

# bisco ablate improvements (JOIN DEFAULT)
df = pd.read_csv(os.path.join(CSV_DIR, 'miplib_improvements_100k.csv'))
df = pd.concat((df, df_default))
df = fill_in_missing_problems(df, miplib_instances)
gen_solved_problems_plots_split_tol(df, 'miplib_improvements', True)
outputs = gen_total_solved_problems_table_split_tol(
    df, 'miplib_improvements', PAR)

def improvements_plot(dfs, prefix, key, ascending):
    normalized_dfs = []
    for df in dfs:
        df = df.sort_values(key, ascending=ascending)
        df[key] = df[key] / (df[key].min() if ascending else df[key].max())
        normalized_dfs.append(df)
    df = pd.concat(normalized_dfs)
    df.set_index('Experiment', inplace=True)
    fig, ax = plt.subplots()
    for tol in df['tolerance'].unique():
        df[df['tolerance'] == tol].plot(ax=ax,
                legend=True, y=key,
                label=f'tolerance {tol:.0E}',
                ylabel=key, figsize=(10, 6),
                title=sanitize_title(prefix),
                xlabel='Improvement', logy=True)
    if len(dfs) == 1:
        ax.get_legend().remove()
    name = key.replace(' ', '_')
    path = os.path.join(FIGS_DIR, f'{prefix}_{name}.pdf')
    plt.savefig(
        path,
        bbox_inches="tight")

for tol, df in outputs.items():
    df = df.copy()
    df['tolerance'] = tol
    improvements_plot(
        (df,),
        'miplib_improvements' +
        f'_tol_{tol:.0E}',
        'KKT passes SGM10',
        ascending=False)
    improvements_plot(
        (df,),
        'miplib_improvements' +
        f'_tol_{tol:.0E}',
        'Solve time secs SGM10',
        ascending=False)
    improvements_plot(
        (df,),
        'miplib_improvements' +
        f'_tol_{tol:.0E}',
        'Solved count',
        ascending=True)

dfs = []
for tol, df in outputs.items():
    df = df.copy()
    df['tolerance'] = tol
    dfs.append(df)
improvements_plot(
    dfs,
    'miplib_improvements',
    'KKT passes SGM10',
    ascending=False)
improvements_plot(
    dfs,
    'miplib_improvements',
    'Solve time secs SGM10',
    ascending=False)
improvements_plot(
    dfs,
    'miplib_improvements',
    'Solved count',
    ascending=True)

