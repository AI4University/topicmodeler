"""
Compute some additional measures when creating models such as memory or cpu usage
"""

import pandas as pd
import datetime as DT
import multiprocessing as mp
import logging
import json
# import shutil
import sys
import time
import warnings
from getpass import getuser
from itertools import product
from pathlib import Path
from random import choices
from typing import Union

sys.path.insert(0, Path(__file__).parent.parent.resolve().as_posix())

from src.topicmodeling.manageModels import TMmodel
from src.topicmodeling.topicmodeling import (CTMTrainer, MalletTrainer,
                                             ProdLDATrainer)
from src.utils.mem_usage import Mem

warnings.filterwarnings(action="ignore")

####################################################
################### TO BE FILLED ###################
####################################################
# Parameters
models = Path("/Users/joseantem/Documents/TM/models/")
origCFile_txt = Path("/Users/joseantem/Documents/datasets/corpus/cordis_lemmas.txt")
origCFile_par = Path("/Users/joseantem/Documents/datasets/corpus/cordis_full.parquet")
mallet_path = Path("/Users/joseantem/Documents/mallet-2.0.8/bin/mallet")
lblFile = Path("/Users/joseantem/Documents/github/topicmodeler/wordlists/wiki_categories.json")
####################################################

# Fixed params
fixed_params = {
    "activation": "softplus",
    "alpha": 5.0,
    "batch_size": 64,
    "doc_topic_thr": 0.0,
    "dropout": 0.2,
    "hidden_sizes": (50, 50),
    "labels": "",
    "learn_priors": True,
    "lr": 2e-3,
    "mallet_path": mallet_path,
    "momentum": 0.99,
    "num_data_loader_workers": mp.cpu_count(),
    "num_threads": 4,
    "optimize_interval": 10,
    "reduce_on_plateau": False,
    "sbert_model_to_load": "paraphrase-distilroberta-base-v1",
    "solver": "adam",
    "thetas_thr": 0.003,
    "token_regexp": "[\\p{L}\\p{N}][\\p{L}\\p{N}\\p{P}]*\\p{L}",
    "topic_prior_mean": 0.0,
    "topic_prior_variance": None,
}
# Tuned params
tuned_params = {
    "ctm_model_type": None,
    "model_type": None,
    "ntopics": None,
    "num_epochs": None,
    "num_iterations": None,
    "num_samples": None,
}

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
logger.addHandler(handler)


def mem_use(fname, processes, gpu=False):
    m = Mem(user=getuser(), processes=processes, gpu=gpu)
    m.proc_info(f"{fname}.txt")


def copy_sampled_corpus(origCFile: Path, corpusFile: Path, samp: Union[int, float]):
    """Saves a sample of the original origCFile into selected corpusFile"""
    if not origCFile.is_file():
        print(
            f"Error: File '{origCFile.resolve().as_posix()}' does not exist.")
        return

    if isinstance(samp, float) and (samp > 1 or samp < 0):
        print(
            "Error: Not valid sample. If 'float', it must be in range [0, 1]")
        return

    if origCFile.suffix == ".txt":
        with origCFile.open("r") as f:
            corpus = f.readlines()
        with corpusFile.open("w") as f:
            if isinstance(samp, float):
                samp = int(samp * len(corpus))
            f.writelines(choices(corpus, k=samp))

    elif origCFile.suffix == '.parquet':
        # TODO: import with spark
        # try:
        #     df = spark.read.parquet(origCFile)
        #     if isinstance(samp, int):
        #         frac = samp/df.count()
        #     else:
        #         frac = samp
        #     return df.sample(False, frac, seed=1)

        # except:
        df = pd.read_parquet(origCFile)
        if isinstance(samp, float):
            df = df.sample(frac=samp, replace=False)
        elif isinstance(samp, int):
            df = df.sample(n=samp, replace=False)
        df.to_parquet(corpusFile)


def get_model_config(trainer, TMparam):
    """Select model configuration based on trainer"""
    if trainer == 'mallet':
        fields = ["ntopics",
                  "thetas_thr",
                  "labels",
                  "mallet_path",
                  "alpha",
                  "optimize_interval",
                  "num_threads",
                  "num_iterations",
                  "doc_topic_thr",
                  "token_regexp"]

    elif trainer == 'sparkLDA':
        fields = []

    elif trainer == 'prodLDA':
        fields = ["n_components",
                  "thetas_thr",
                  "labels",
                  "model_type",
                  "hidden_sizes",
                  "activation",
                  "dropout",
                  "learn_priors",
                  "lr",
                  "momentum",
                  "solver",
                  "num_epochs",
                  "reduce_on_plateau",
                  "batch_size",
                  "topic_prior_mean",
                  "topic_prior_variance",
                  "num_samples",
                  "num_data_loader_workers", ]

    elif trainer == 'ctm':
        fields = ["n_components",
                  "thetas_thr",
                  "labels",
                  "model_type",
                  "ctm_model_type",
                  "hidden_sizes",
                  "activation",
                  "dropout",
                  "learn_priors",
                  "lr",
                  "momentum",
                  "solver",
                  "num_epochs",
                  "reduce_on_plateau",
                  "batch_size",
                  "topic_prior_mean",
                  "topic_prior_variance",
                  "num_samples",
                  "num_data_loader_workers", ]

    params = {"trainer": trainer, "TMparam": {t: TMparam[t] for t in fields}}
    return params


def train_model(train_config, corpusFile, embeddingsFile=None):
    """Train a model based on train_config, using corpusFile and embeddingsFile"""
    trainer = train_config["trainer"]
    TMparam = train_config["TMparam"]

    if trainer == 'mallet':
        trainer = MalletTrainer(**TMparam, logger=logger)

    # elif trainer == 'sparkLDA':
    #     sparkLDATr = sparkLDATrainer()

    elif trainer == 'prodLDA':
        trainer = ProdLDATrainer(**TMparam, logger=logger)

    elif trainer == 'ctm':
        trainer = CTMTrainer(**TMparam, logger=logger)

    if trainer == 'ctm' and train_config['hierarchy-level'] == 1:
        trainer.fit(corpusFile=corpusFile, embeddingsFile=embeddingsFile)
    else:
        trainer.fit(corpusFile=corpusFile)


def main():
    # Create folder structure
    # TODO:
    models.mkdir(parents=True, exist_ok=True)

    # Iterate configuration
    # Define values for tunable parameters
    topicModelTypes = ["mallet", "prodLDA", "ctm", "sparkLDA"]
    coherences = ["c_npmi", "u_mass"]  # c_npmi is computed by default
    ########################################
    # TODO:
    number_topics = [10, 20]
    number_iterations = [100, 500]
    number_threads = [2, 4, 8]
    number_samples = [10, 20]
    number_epochs = [10]
    model_types = ["prodLDA", "LDA"]
    ctm_model_types = ["ZeroShotTM", "CombinedTM"]
    number_docs = [5000, 10000]
    ########################################

    for trainer in topicModelTypes[:3]:
        if trainer == "mallet":
            param_conf = ({"ndocs": d, "ntopics": n, "num_iterations": i, "num_threads": t}
                          for d, n, i, t in product(number_docs, number_topics, number_iterations, number_threads))
            origCFile = origCFile_txt
            CFtype = "txt"
            processes = ["python3", "java"]
            use_gpu = False
        elif trainer == "prodLDA":
            param_conf = ({"ndocs": d, "n_components": n, "num_samples": s, "num_epochs": e, "model_type": m}
                          for d, n, s, e, m in product(number_docs, number_topics, number_samples, number_epochs, model_types))
            origCFile = origCFile_par
            CFtype = "parquet"
            processes = ["python3"]
            use_gpu = True
        elif trainer == "ctm":
            param_conf = ({"ndocs": d, "n_components": n, "num_samples": s, "num_epochs": e, "model_type": m, "ctm_model_type": t}
                          for d, n, s, e, m, t in product(number_docs, number_topics, number_samples, number_epochs, model_types, ctm_model_types))
            origCFile = origCFile_par
            CFtype = "parquet"
            processes = ["python3"]
            use_gpu = True

        else:
            logger.error("Not valid trainer")
            exit()

        for tuned_params in param_conf:
            # Set configuration
            TMparam = {**fixed_params, **tuned_params}
            train_config = get_model_config(trainer, TMparam)

            # Save configuration
            model_path = models.joinpath(
                f"{trainer}_{'_'.join(f'{i}' for i in tuned_params.values())}_{DT.datetime.now().strftime('%Y%m%d')}")
            model_path.mkdir(parents=True, exist_ok=True)
            model_stats = model_path.joinpath("stats")
            model_stats.mkdir(parents=True, exist_ok=True)
            tuned_params_conf = model_stats.joinpath("tuned_params.json")
            with tuned_params_conf.open("w", encoding="utf-8") as fout:
                tuned_params = {"trainer": trainer, **tuned_params}
                json.dump(tuned_params, fout, ensure_ascii=False,
                          indent=2, default=str)
            config_file = model_path.joinpath("config.json")
            with config_file.open("w", encoding="utf-8") as fout:
                json.dump(train_config, fout, ensure_ascii=False,
                          indent=2, default=str)
            tm = TMmodel(model_path.joinpath("TMmodel"))

            # Copy corpus to model path
            corpusFile = config_file.parent.joinpath(f"corpus.{CFtype}")
            copy_sampled_corpus(origCFile, corpusFile, tuned_params["ndocs"])
            # shutil.copy(origCFile, corpusFile)

            # Start memory usage script
            logger.info("-- Started measuring memory")
            thrd = mp.Process(target=mem_use, args=(model_stats.joinpath("mem_use"), processes, use_gpu))
            thrd.start()
            time.sleep(1)

            # Execute command
            # cmd = f"python3 src/topicmodeling/topicmodeling.py --config {config_file.resolve().as_posix()} --train"
            # logger.info(f"Running command '{cmd}'")
            t_start = time.perf_counter()

            # Train model
            train_model(train_config, corpusFile)

            # Compute coherences
            coh_stats = []
            for c in coherences:
                tc_start = time.perf_counter()
                tm.calculate_topic_coherence(metric=c)
                coh = tm._topic_coherence
                tc_end = time.perf_counter()
                coh_stats.append(
                    {"measure": c, "coherences": coh, "time": tc_end-tc_start})
            with model_stats.joinpath(f"topic_coherence.json").open("w") as fout:
                json.dump(coh_stats, fout, ensure_ascii=False,
                          indent=2, default=str)

            t_end = time.perf_counter()
            thrd.terminate()
            time.sleep(1)
            logger.info("-- Finished measuring memory")

            ######################################################################################
            # logger.info("-- Computing topic labels outside memory measure")
            # labels = []
            # if lblFile.is_file():
            #     with Path(lblFile).open('r', encoding='utf8') as fin:
            #         labels += json.load(fin)['wordlist']
            # tpc_labels = [el[1] for el in tm.get_tpc_labels(labels)]
            # with tm._TMfolder.joinpath('tpc_labels.txt').open('w', encoding='utf8') as fout:
            #     fout.write('\n'.join(tpc_labels))
            # logger.info("-- Finished topic labeling")
            ######################################################################################

            t_total = t_end - t_start
            logger.info(f"Total time --> {t_total}")
            print("\n")
            print("-" * 100)
            print("\n")


if __name__ == "__main__":
    main()
