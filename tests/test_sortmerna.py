#!/usr/bin/env python
"""
Software tests for the SortMeRNA
================================
"""


import unittest
import re
import sys
from subprocess import Popen, PIPE, run
from os import close, remove, environ, listdir, unlink
from os.path import abspath, exists, join, dirname, isfile
from tempfile import mkstemp, mkdtemp
from shutil import rmtree

import skbio.io
import platform
import time

# ----------------------------------------------------------------------------
# Copyright (c) 2014--, Evguenia Kopylova
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

# Some notes on memory debugging:
# Memory check with valgrind --leak-check=full --track-origins=yes
# use -g compile option for line numbers in valgrind and traceback
# with gdb
# "$ export GLIBCXX_FORCE_NEW" to disable std::string memory pool optimizations
# prior to running valgrind

    
# Test class and cases
class SortmernaTests(unittest.TestCase):
    """ Tests for SortMeRNA functionality """
    
    @classmethod
    def setUpClass(self):
        self.sortmerna = 'sortmerna'
        self.indexdb_rna = 'indexdb'

    def setUp(self):
        self.output_dir = mkdtemp()
        # 'data' folder must be in the same directory as test_sortmerna.py
        self.root = join(dirname(abspath(__file__)), "data")
        
        # reference databases
        self.db_bac16s = join(self.root, "silva-bac-16s-database-id85.fasta")
        self.db_arc16s = join(self.root, "silva-arc-16s-database-id95.fasta")
        self.db_gg_13_8 = join(self.root, "gg_13_8_ref_set.fasta")
        self.db_GQ099317 = join(self.root, "ref_GQ099317_forward_and_rc.fasta")
        self.db_short = join(self.root, "ref_short_seqs.fasta")
        
        # reads
        self.set2 = join(self.root, "set2_environmental_study_550_amplicon.fasta")
        self.set3 = join(self.root, "empty_file.fasta")
        self.set4 = join(self.root, "set4_mate_pairs_metatranscriptomics.fastq")
        self.set5 = join(self.root, "set5_simulated_amplicon_silva_bac_16s.fasta")
        self.set7 = join(self.root, "set7_arc_bac_16S_database_match.fasta")
        self.read_GQ099317 = join(self.root, "illumina_GQ099317.fasta")
        
        # create temporary file with reference sequence
        f, self.subject_str_fp = mkstemp(prefix='temp_subject_', suffix='.fasta')
        close(f)
        # write _reference_ sequences to tmp file
        with open(self.subject_str_fp, 'w') as tmp:
            tmp.write(subject_str)
        tmp.close()
        # create temporary file with query sequence
        f, self.query_str_fp = mkstemp(prefix='temp_query_',
                                       suffix='.fasta')
        close(f)
        # write _query_ sequences to tmp file
        with open(self.query_str_fp, 'w') as tmp:
            tmp.write(query_str)
        tmp.close()
        self.files_to_remove = [self.subject_str_fp, self.query_str_fp]
        self.ALIGN_REPORT = '4'
        self.ONLY_REPORT = '2'

    def tearDown(self):
        rmtree(self.output_dir)
        for file in self.files_to_remove:
            remove(file)

    def test_ref_shorter_than_seed(self):
        """ Test building a database where at least
            one reference sequence is shorter than the
            seed length
        """
        print("test_ref_shorter_than_seed")
        start = time.time()
        
        index_db = join(self.output_dir, "ref_short_seqs.fasta")
        index_path = "%s,%s" % (self.db_short, index_db)
        
        indexdb_command = [self.indexdb_rna,
                           "--ref", index_path]
        
        print('test_ref_shorter_than_seed: {}'.format(indexdb_command))
        
        if 'Windows' in platform.platform():
            proc = run(indexdb_command, stdout=PIPE, stderr=PIPE)
        else:
            proc = Popen(indexdb_command,
                         stdout=PIPE,
                         stderr=PIPE,
                         close_fds=True)
            proc.wait()
            stdout, stderr = proc.communicate()
            proc.stdout.close()
            proc.stderr.close()
            self.assertTrue(stderr)
            error_msg = """at least one of your sequences is shorter than the seed length 19, please filter out all sequences shorter than 19 to continue index construction"""
            print("test_ref_shorter_than_seed: Asserting [{}] in [{}]".format(error_msg, stderr))
            self.assertTrue(error_msg in stderr.decode('utf-8'))
            
        print("test_ref_shorter_than_seed: Run time: {}".format(time.time() - start))
    #END test_ref_shorter_than_seed

    def test_indexdb_rna_tmpdir_arg(self):
        """ Test writing to --tmpdir
        """
        print("test_indexdb_rna_tmpdir_arg")
        start = time.time()
        
        tmpdir = mkdtemp()
        index_db = join(self.output_dir, "GQ099317")
        index_path = "%s,%s" % (self.db_GQ099317, index_db)
        
        indexdb_command = [self.indexdb_rna,
                           "--ref", index_path,
                           "--tmpdir", tmpdir,
                           "-v"]
        
        print('test_indexdb_rna_tmpdir_arg: {}'.format(indexdb_command))
        
        if 'Windows' in platform.platform():
            proc = run(indexdb_command, stdout=PIPE, stderr=PIPE)
            stdout = proc.stdout
        else:
            proc = Popen(indexdb_command,
                         stdout=PIPE,
                         stderr=PIPE,
                         close_fds=True)
            proc.wait()
            stdout, stderr = proc.communicate()
            proc.stdout.close()
            proc.stderr.close()
            self.assertTrue(stdout)
            self.assertFalse(stderr)
            
        expected_db_files = set(index_db + ext
                                for ext in ['.bursttrie_0.dat', '.kmer_0.dat',
                                            '.pos_0.dat', '.stats'])
        for fp in expected_db_files:
            self.assertTrue(exists(fp))
            
        # check temporary folder was that set by --tmpdir
        query = re.compile(b'temporary file was here: (.*?)\n')
        m = query.search(stdout)
        tmp_dir = ""
        if m:
            tmp_dir = dirname(m.group(1)).decode("utf-8")
        self.assertEqual(tmpdir, tmp_dir)
        rmtree(tmpdir)
            
        print("test_indexdb_rna_tmpdir_arg: Run time: {}".format(time.time() - start))
    #END test_indexdb_rna_tmpdir_arg

    def test_indexdb_rna_TMPDIR_env(self):
        """ Test writing to TMPDIR env variable
        """
        print("test_indexdb_rna_TMPDIR_env")
        start = time.time()
        
        tmpdir = mkdtemp()
        if 'Windows' in platform.platform():
            environ["TMP"] = tmpdir
        else:
            environ["TMPDIR"] = tmpdir
        index_db = join(self.output_dir, "GQ099317")
        index_path = "%s,%s" % (self.db_GQ099317, index_db)
        
        indexdb_command = [self.indexdb_rna,
                           "--ref", index_path,
                           "-v"]
        
        print('test_indexdb_rna_TMPDIR_env: {}'.format(indexdb_command))
        
        if 'Windows' in platform.platform():
            proc = run(indexdb_command, stdout=PIPE, stderr=PIPE)
            stdout = proc.stdout
        else:
            proc = Popen(indexdb_command,
                         stdout=PIPE,
                         stderr=PIPE,
                         close_fds=True)
            proc.wait()
            stdout, stderr = proc.communicate()
            proc.stdout.close()
            proc.stderr.close()
            self.assertTrue(stdout)
            self.assertFalse(stderr)
            
        expected_db_files = set(index_db + ext
                                for ext in ['.bursttrie_0.dat', '.kmer_0.dat',
                                            '.pos_0.dat', '.stats'])
        for fp in expected_db_files:
            self.assertTrue(exists(fp))
            
        # check temporary folder was that set by --tmpdir
        query = re.compile(b'temporary file was here: (.*?)\n')
        m = query.search(stdout)
        tmp_dir = ""
        if m:
            tmp_dir = dirname(m.group(1)).decode("utf-8")
        self.assertEqual(tmpdir, tmp_dir)
        rmtree(tmpdir)
            
        print("test_indexdb_rna_TMPDIR_env: Run time: {}".format(time.time() - start))
    #END test_indexdb_rna_TMPDIR_env

    def test_indexdb_rna_tmp_dir_system(self):
        """ Test writing to /tmp folder
        """
        FUNC = 'test_indexdb_rna_tmp_dir_system'
        print(FUNC)
        start = time.time()
        
        if 'Windows' in platform.platform():
            environ["TMP"] = ""
        else:
            environ["TMPDIR"] = ""
        index_db = join(self.output_dir, "GQ099317")
        index_path = "%s,%s" % (self.db_GQ099317, index_db)
        
        cmd = [self.indexdb_rna,
                           "--ref", index_path,
                           "-v"]
        
        print('{}: {}'.format(FUNC, ' '.join(cmd)))
        
        if 'Windows' in platform.platform():
            proc = run(cmd, stdout=PIPE, stderr=PIPE)
            stdout = proc.stdout
        else:
            proc = Popen(cmd,
                         stdout=PIPE,
                         stderr=PIPE,
                         close_fds=True)
            proc.wait()
            stdout, stderr = proc.communicate()
            proc.stdout.close()
            proc.stderr.close()
            self.assertTrue(stdout)
            self.assertFalse(stderr)
            
        expected_db_files = set(index_db + ext
                                for ext in ['.bursttrie_0.dat', '.kmer_0.dat',
                                            '.pos_0.dat', '.stats'])
        for fp in expected_db_files:
            self.assertTrue(exists(fp))
        # check temporary folder was that set by --tmpdir
        query = re.compile(b'temporary file was here: (.*?)\n')
        print('stdout: {}'.format(stdout))
        m = query.search(stdout)
        
        if 'Windows' in platform.platform():
            tmp_dir = environ.get('TMP')
            print('TEMP: {}'.format(tmp_dir))
        else:
            if m: tmp_dir = dirname(m.group(1).decode('utf-8'))
            self.assertEqual("/tmp", tmp_dir)
            
        print("test_indexdb_rna_tmp_dir_system: Run time: {}".format(time.time() - start))
    #END test_indexdb_rna_tmp_dir_system

    def test_indexdb_default_param(self):
        """ Test indexing a database using SortMeRNA
        """
        print("test_indexdb_default_param")
        start = time.time()
        
        index_db = join(self.output_dir, "db_gg_13_8")
        index_path = "%s,%s" % (self.db_gg_13_8, index_db)
        
        indexdb_command = [self.indexdb_rna,
                           "--ref", index_path,
                           "-v"]
        
        print('test_indexdb_default_param: {}'.format(indexdb_command))
        
        if 'Windows' in platform.platform():
            proc = run(indexdb_command, stdout=PIPE, stderr=PIPE)
        else:
            proc = Popen(indexdb_command,
                         stdout=PIPE,
                         stderr=PIPE,
                         close_fds=True)
            proc.wait()
            stdout, stderr = proc.communicate()
            proc.stdout.close()
            proc.stderr.close()
            self.assertTrue(stdout)
            self.assertFalse(stderr)
            
        expected_db_files = set(index_db + ext
                                for ext in ['.bursttrie_0.dat', '.kmer_0.dat',
                                            '.pos_0.dat', '.stats'])
        # Make sure all db_files exist
        for fp in expected_db_files:
            self.assertTrue(exists(fp))
            
        print("test_indexdb_default_param: Run time: {}".format(time.time() - start))
    #END test_indexdb_default_param

    def test_indexdb_split_databases(self):
        """ Test indexing a database using SortMeRNA
            with m = 0.05, that is 7 parts
        """
        print("test_indexdb_split_databases")
        start = time.time()
        
        index_db = join(self.output_dir, "db_gg_13_8")
        index_path = "%s,%s" % (self.db_gg_13_8, index_db)
        
        indexdb_command = [self.indexdb_rna,
                           "--ref", index_path,
                           "-v",
                           "-m ", "0.05"]
        
        print('test_indexdb_split_databases: {}'.format(indexdb_command))
        
        if 'Windows' in platform.platform():
            proc = run(indexdb_command, stdout=PIPE, stderr=PIPE)
        else:
            proc = Popen(indexdb_command,
                         stdout=PIPE,
                         stderr=PIPE,
                         close_fds=True)
            proc.wait()
            stdout, stderr = proc.communicate()
            proc.stdout.close()
            proc.stderr.close()
            self.assertFalse(stderr)
            self.assertTrue(stdout)
            
        expected_db_files = set(index_db + ext
                                for ext in ['.bursttrie_0.dat',
                                            '.bursttrie_1.dat',
                                            '.bursttrie_2.dat',
                                            '.bursttrie_3.dat',
                                            '.bursttrie_4.dat',
                                            '.bursttrie_5.dat',
                                            '.bursttrie_6.dat',
                                            '.kmer_0.dat',
                                            '.kmer_1.dat',
                                            '.kmer_2.dat',
                                            '.kmer_3.dat',
                                            '.kmer_4.dat',
                                            '.kmer_5.dat',
                                            '.kmer_6.dat',
                                            '.pos_0.dat',
                                            '.pos_1.dat',
                                            '.pos_2.dat',
                                            '.pos_3.dat',
                                            '.pos_4.dat',
                                            '.pos_5.dat',
                                            '.pos_6.dat',
                                            '.stats'])

        # Make sure all db_files exist
        for fp in expected_db_files:
            self.assertTrue(exists(fp))
            
        print("test_indexdb_split_databases: Run time: {}".format(time.time() - start))
    #END test_indexdb_split_databases

    def test_multiple_databases_search(self):
        """ Test sortmerna on 6 reads against
            arc-16s and bac-16s databases.
            4/6 reads match both arc-16s and
            bac-16s and 2/6 are random reads.
        """
        print("test_multiple_databases_search")
        start = time.time()
        
        if 'Windows' in platform.platform():
            separator = ';'
        else:
            separator = ':'
            
        index_path = "%s,%s%s%s,%s" % (self.db_bac16s,
                                      join(self.output_dir, "db_bac16s"),
                                      separator,
                                      self.db_arc16s,
                                      join(self.output_dir, "db_arc16s"))
        
        datadir = join(self.output_dir, 'kvdb')
        
        indexdb_command = [self.indexdb_rna,
                           "--ref", index_path,
                           "-v"]
        
        print('test_multiple_databases_search: {}'.format(indexdb_command))
        
        proc = run(indexdb_command, stdout=PIPE, stderr=PIPE)
        aligned_basename = join(self.output_dir, "aligned")
        
        sortmerna_command = [self.sortmerna,
                             "--ref", index_path,
                             "--reads", self.set7,
                             "--aligned", aligned_basename,
                             "--log",
                             "--fastx",
                             "-d", datadir,
                             "--task", self.ALIGN_REPORT]
        
        print('test_multiple_databases_search: {}'.format(sortmerna_command))
        
        proc = run(sortmerna_command, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)
        
        f_log = open(aligned_basename + ".log")
        f_log_str = f_log.read()
        self.assertTrue("Total reads passing E-value threshold" in f_log_str)
        self.assertTrue("Total reads failing E-value threshold" in f_log_str)
        f_log.seek(0)
        for line in f_log:
            if line.startswith("    Total reads = "):
                total_reads_log = (re.split(' = ', line)[1]).strip()
            elif line.startswith("    Total reads passing E-value threshold"):
                num_hits_log = (re.split(' = | \(', line)[1]).strip()
        f_log.close()
        # Correct number of reads
        self.assertEqual("6", total_reads_log)
        # Correct number of reads mapped
        self.assertEqual("4", num_hits_log)
        num_hits_file = 0
        for seq in skbio.io.read(aligned_basename + ".fasta", format='fasta'):
            num_hits_file += 1
        self.assertEqual(num_hits_log, str(num_hits_file))
            
        print("test_multiple_databases_search: Run time: {}".format(time.time() - start))
    #END test_multiple_databases_search

    def output_test(self, aligned_basename, other_basename):
        """ Test output of unit test functions.
            Used by:
                test_simulated_amplicon_1_part_map
                test_simulated_amplicon_generic_buffer
                test_simulated_amplicon_12_part_index
        """
        f_log = open(aligned_basename + ".log")
        f_log_str = f_log.read()
        self.assertTrue("Total reads passing E-value threshold" in f_log_str)
        self.assertTrue("Total reads for de novo clustering" in f_log_str)
        self.assertTrue("Total OTUs" in f_log_str)
        
        num_pass_id_cov_log = ''
        
        f_log.seek(0)
        for line in f_log:
            if 'Total reads =' in line:
                total_reads_log = (re.split(' = ', line)[1]).strip()
            elif 'Total reads for de novo clustering' in line:
                num_denovo_log = (re.split(' = ', line)[1]).strip()
            elif 'Total reads passing E-value threshold' in line:
                num_hits_log = (re.split(' = | \(', line)[1]).strip()
            elif 'Total reads failing E-value threshold' in line:
                num_fails_log = (re.split(' = | \(', line)[1]).strip()
            elif 'Total reads passing' in line and 'id' in line and 'coverage thresholds' in line:
                num_pass_id_cov_log = (re.split(' = ', line)[1]).strip()
            elif 'Total OTUs' in line:
                num_clusters_log = (re.split('Total OTUs = ', line)[1]).strip()
        f_log.close()
        
        # Correct number of reads
        self.assertEqual("30000", total_reads_log)
        
        # Correct number of de novo reads
        self.assertEqual("9831", num_denovo_log)
        num_denovo_file = 0
        for seq in skbio.io.read(aligned_basename + "_denovo.fasta", format='fasta'):
            num_denovo_file += 1
        self.assertEqual(num_denovo_log, str(num_denovo_file))
        
        # Correct number of reads mapped
        self.assertEqual("19995", num_hits_log)
        num_hits_file = 0
        for seq in skbio.io.read(aligned_basename + ".fasta", format='fasta'):
            num_hits_file += 1
        self.assertEqual(num_hits_log, str(num_hits_file))
        
        # Correct number of reads not mapped
        self.assertEqual("10005", num_fails_log)
        num_fails_file = 0
        for seq in skbio.io.read(other_basename + ".fasta", format='fasta'):
            num_fails_file += 1
        self.assertEqual(num_fails_log, str(num_fails_file))
        
        # Correct number of reads passing %id and %coverage threshold
        self.assertEqual("10164", num_pass_id_cov_log)
        num_pass_id_cov_file = 0
        with open(aligned_basename + ".blast") as f_blast:
            for line in f_blast:
                f_id = float(line.strip().split('\t')[2])
                f_cov = float(line.strip().split('\t')[13])
                if (f_id >= 97.0 and f_cov >= 97.0):
                    num_pass_id_cov_file += 1
        self.assertEqual(num_pass_id_cov_log, str(num_pass_id_cov_log))
        
        # Correct number of clusters recorded
        #self.assertEqual("4401", num_clusters_log) # 4400 before bug 52
        self.assertTrue(num_clusters_log in ['4400','4401']) # 4400 for amplicon_12_part
        num_clusters_file = 0
        num_reads_in_clusters_file = 0
        with open(aligned_basename + "_otus.txt") as f_otus:
            for line in f_otus:
                num_clusters_file += 1
                num_reads_in_clusters_file += (len(line.strip().split('\t'))-1)
        self.assertEqual(num_clusters_log, str(num_clusters_file))
        self.assertEqual(num_pass_id_cov_log, str(num_reads_in_clusters_file))

    def test_simulated_amplicon_1_part_map(self):
        """ Test sortmerna on simulated data,
            10000 reads with 1% error (--aligned),
            10000 reads with 10% error (de novo),
            10000 reads random (--other)

            Conditions: reference index and input
            query FASTA file both processed as one
            section.
        """
        FUNC = "test_simulated_amplicon_1_part_map"
        print(FUNC)
        start = time.time()
        
        index_db = join(self.output_dir, "db_bac16s")
        index_path = "%s,%s" % (self.db_bac16s, index_db)
        datadir = join(self.output_dir, 'kvdb')
        aligned_basename = join(self.output_dir, "aligned")
        other_basename = join(self.output_dir, "other")
        
        indexdb_command = [self.indexdb_rna,
                           "--ref", index_path,
                           "-v"]
        
        print('{}: {}'.format(FUNC, indexdb_command))
        
        if 'Windows' in platform.platform():
            proc = run(indexdb_command, stdout=PIPE, stderr=PIPE)
        else:
            proc = Popen(indexdb_command,
                         stdout=PIPE,
                         stderr=PIPE,
                         close_fds=True)
            proc.wait()
            proc.stdout.close()
            proc.stderr.close()
            
        # best 1
        sortmerna_command = [self.sortmerna,
                             "--ref", index_path,
                             "--reads", self.set5,
                             "--aligned", aligned_basename,
                             "--other", other_basename,
                             "--id", "0.97",
                             "--coverage", "0.97",
                             "--log",
                             "--otu_map",
                             "--de_novo_otu",
                             "--blast", "1 cigar qcov",
                             "--fastx",
                             "-v",
                             "-d", datadir,
                             "--task", self.ALIGN_REPORT]
        
        print('{}: {}'.format(FUNC, sortmerna_command))
        
        if 'Windows' in platform.platform():
            proc = run(sortmerna_command, stdout=PIPE, stderr=PIPE)
            stderr = proc.stderr
        else:
            proc = Popen(sortmerna_command,
                         stdout=PIPE,
                         stderr=PIPE,
                         close_fds=True)
            proc.wait()
            stdout, stderr = proc.communicate()
            proc.stdout.close()
            proc.stderr.close()
            
        if stderr: print(stderr)
        
        self.output_test(aligned_basename, other_basename)
        
        # Clean up before next call
        remove(aligned_basename + ".log")
        remove(aligned_basename + ".fasta")
        remove(aligned_basename + "_otus.txt")
        remove(aligned_basename + "_denovo.fasta")
        remove(aligned_basename + ".blast")
        remove(other_basename + ".fasta")
        self.cleanData(datadir)
        
        # best 5
        sortmerna_command = [self.sortmerna,
                             "--ref", index_path,
                             "--reads", self.set5,
                             "--aligned", aligned_basename,
                             "--other", other_basename,
                             "--id", "0.97",
                             "--coverage", "0.97",
                             "--log",
                             "--otu_map",
                             "--de_novo_otu",
                             "--blast", "1 cigar qcov",
                             "--fastx",
                             "--best", "5",
                             "-v",
                             "-d", datadir,
                             "--task", self.ALIGN_REPORT]
        
        print('{}: {}'.format(FUNC, sortmerna_command))
        
        if 'Windows' in platform.platform():
            proc = run(sortmerna_command, stdout=PIPE, stderr=PIPE)
            stderr = proc.stderr
        else:
            proc = Popen(sortmerna_command,
                         stdout=PIPE,
                         stderr=PIPE,
                         close_fds=True)
            proc.wait()
            stdout, stderr = proc.communicate()
            proc.stdout.close()
            proc.stderr.close()
            
        if stderr: print(stderr)
        self.output_test(aligned_basename, other_basename)
            
        print("{}: Run time: {}".format(FUNC, time.time() - start))
    #END test_simulated_amplicon_1_part_map
        
    def cleanData(self, datadir):
        '''
        '''
        for file in listdir(datadir):
            fpath = join(datadir, file)
            try:
                if isfile(fpath): unlink(fpath)
                #elif os.path.isdir(fpath): shutil.rmtree(fpath)
            except Exception as e:
                print(e)

    def test_simulated_amplicon_generic_buffer(self):
        """ Test sortmerna on simulated data,
            10000 reads with 1% error (--aligned),
            10000 reads with 10% error (de novo),
            10000 reads random (--other)

            Conditions: reference index and input
            query FASTA file both processed as one
            section using the generic buffer (kseq lib).
        """
        FUNC = "test_simulated_amplicon_generic_buffer"
        print(FUNC)
        start = time.time()
        
        index_db = join(self.output_dir, "db_bac16s")
        index_path = "%s,%s" % (self.db_bac16s, index_db)
        datadir = join(self.output_dir, 'kvdb')
        
        cmd = [self.indexdb_rna, "--ref", index_path, "-v"]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))

        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)

        aligned_basename = join(self.output_dir, "aligned")
        other_basename = join(self.output_dir, "other")
        
        # best 1
        cmd = [self.sortmerna,
                "--ref", index_path,
                "--reads", self.set5,
                "--aligned", aligned_basename,
                "--other", other_basename,
                "--id", "0.97",
                "--coverage", "0.97",
                "--log",
                "--otu_map",
                "--de_novo_otu",
                "--blast", "1 cigar qcov",
                "--fastx",
                "-v",
                "-d", datadir]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)
        self.output_test(aligned_basename, other_basename)
        
        # Clean up before next call
        remove(aligned_basename + ".log")
        remove(aligned_basename + ".fasta")
        remove(aligned_basename + "_otus.txt")
        remove(aligned_basename + "_denovo.fasta")
        remove(aligned_basename + ".blast")
        remove(other_basename + ".fasta")
        self.cleanData(datadir)
        
        # best 5
        cmd = [self.sortmerna,
                "--ref", index_path,
                "--reads", self.set5,
                "--aligned", aligned_basename,
                "--other", other_basename,
                "--id", "0.97",
                "--coverage", "0.97",
                "--log",
                "--otu_map",
                "--de_novo_otu",
                "--blast", "1 cigar qcov",
                "--fastx",
                "--best", "5",
                "-v",
                "-d", datadir,
                "--task", self.ALIGN_REPORT]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))

        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)
        self.output_test(aligned_basename, other_basename)
            
        print("{}: Run time: {}".format(FUNC, time.time() - start))
    #END test_simulated_amplicon_generic_buffer

    def test_simulated_amplicon_6_part_map(self):
        """ Test sortmerna on simulated data,
            10000 reads with 1% error (--aligned),
            10000 reads with 10% error (de novo),
            10000 reads random (--other)

            Conditions: reference index processed
            as one unit and input query FASTA file
            in 6 sections.
        """
        FUNC = 'test_simulated_amplicon_6_part_map'
        print(FUNC)
        start = time.time()
        
        index_db = join(self.output_dir, "db_bac16s")
        index_path = "%s,%s" % (self.db_bac16s, index_db)
        datadir = join(self.output_dir, 'kvdb')
        
        cmd = [self.indexdb_rna,
                "--ref", index_path,
                "-v"]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        if 'Windows' in platform.platform():
            proc = run(cmd, stdout=PIPE, stderr=PIPE)
        else:
            proc = Popen(cmd, stdout=PIPE,  stderr=PIPE, close_fds=True)
            proc.wait()
            proc.stdout.close()
            proc.stderr.close()
            
        aligned_basename = join(self.output_dir, "aligned")
        other_basename = join(self.output_dir, "other")
        
        cmd = [self.sortmerna,
                "--ref", index_path,
                "--reads", self.set5,
                "--aligned", aligned_basename,
                "--other", other_basename,
                "--id", "0.97",
                "--coverage", "0.97",
                "--log",
                "--otu_map",
                "--de_novo_otu",
                "--blast", "1 cigar qcov",
                "--fastx",
                "-v",
                "-d", datadir]
        
        print("{}: {}".format(FUNC, cmd))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)

        self.output_test(aligned_basename, other_basename)
            
        print("{}: Run time: {}".format(FUNC, time.time() - start))
    #END test_simulated_amplicon_6_part_map

    def test_simulated_amplicon_12_part_index(self):
        """ Test sortmerna on simulated data,
            10000 reads with 1% error (--aligned),
            10000 reads with 10% error (de novo),
            10000 reads random (--other)

            Conditions: reference index processed
            as 12 parts and input query FASTA file
            in 1 section.
        """
        print("test_simulated_amplicon_12_part_index")
        start = time.time()
        
        index_db = join(self.output_dir, "db_bac16s")
        index_path = "%s,%s" % (self.db_bac16s, index_db)
        datadir = join(self.output_dir, 'kvdb')
        
        cmd = [self.indexdb_rna,
                "--ref", index_path,
                "-v",
                "-m", "10"]
        
        print("test_simulated_amplicon_12_part_index: {}".format(cmd))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)

        aligned_basename = join(self.output_dir, "aligned")
        other_basename = join(self.output_dir, "other")
        
        cmd = [self.sortmerna,
                "--ref", index_path,
                "--reads", self.set5,
                "--aligned", aligned_basename,
                "--other", other_basename,
                "--id", "0.97",
                "--coverage", "0.97",
                "--log",
                "--otu_map",
                "--de_novo_otu",
                "--blast", "1 cigar qcov",
                "--fastx",
                "-v",
                "-d", datadir,
                "--task", self.ALIGN_REPORT]
        
        print("test_simulated_amplicon_12_part_index: {}".format(cmd))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)
        
        self.output_test(aligned_basename, other_basename)
            
        print("test_simulated_amplicon_12_part_index: Run time: {}".format(time.time() - start))
    #END test_simulated_amplicon_12_part_index

    def test_environmental_output(self):
        """ Test outputting FASTA file for de novo
            clustering using environmental data.

            Conditions: input FASTA file is processed in
            one mapped section.
        """
        FUNC = 'test_environmental_output'
        print(FUNC)
        start = time.time()
        
        index_db = join(self.output_dir, "db_bac16s")
        index_path = "%s,%s" % (self.db_bac16s, index_db)
        datadir = join(self.output_dir, 'kvdb')
        
        cmd = [self.indexdb_rna,
                "--ref", index_path,
                "--max_pos", "250",
                "-v"]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        aligned_basename = join(self.output_dir, "aligned")
        
        cmd = [self.sortmerna,
                "--ref", index_path,
                "--reads", self.set2,
                "--aligned", aligned_basename,
                "--id", "0.97",
                "--coverage", "0.97",
                "--log",
                "--otu_map",
                "--de_novo_otu",
                "--fastx",
                "-v",
                "-d", datadir,
                "--task", self.ALIGN_REPORT]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        stderr = proc.stderr
        if stderr: print(stderr)
        
        f_log = open(aligned_basename + ".log")
        f_log_str = f_log.read()
        self.assertTrue("Total reads passing E-value threshold" in f_log_str)
        self.assertTrue("Total reads for de novo clustering" in f_log_str)
        self.assertTrue("Total OTUs" in f_log_str)
        f_log.seek(0)
        for line in f_log:
            if line.startswith("    Total reads passing E-value threshold"):
                num_hits = (re.split('Total reads passing E-value threshold = | \(', line)[1]).strip()
            elif line.startswith("    Total reads for de novo clustering"):
                num_failures_log =\
                    (re.split('Total reads for de novo clustering = ',
                              line)[1]).strip()
            elif line.startswith(" Total OTUs"):
                num_clusters_log = (re.split('Total OTUs = ', line)[1]).strip()
        f_log.close()
        # Correct number of reads mapped
        self.assertEqual("99999", num_hits)
        # Correct number of clusters recorded
        use_refs_descending = False # how algorithm sorts candidate references descending/ascending (alignment.cpp)
        if use_refs_descending:
            num_groups = 272 # originally
        else:
            num_groups = 264
        self.assertEqual(str(num_groups), num_clusters_log)
        # Correct number of clusters in OTU-map
        with open(aligned_basename + "_otus.txt") as f_otumap:
            num_clusters_file = sum(1 for line in f_otumap)
        self.assertEqual(num_groups, num_clusters_file)
        num_failures_file = 0
        for seq in skbio.io.read(aligned_basename + "_denovo.fasta", format='fasta'):
            num_failures_file += 1
        # Correct number of reads for de novo clustering
        self.assertEqual(num_failures_log, str(num_failures_file))
            
        print("{}: Run time: {}".format(FUNC, time.time() - start))
    #END test_environmental_output

    def test_empty_query_file(self):
        """ Test SortMeRNA with an empty reads file.
        """
        FUNC = "test_empty_query_file"
        print(FUNC)
        start = time.time()
        
        index_db = join(self.output_dir, "db_gg_13_8")
        index_path = "%s,%s" % (self.db_gg_13_8, index_db)
        datadir = join(self.output_dir, 'kvdb')
        
        cmd = [self.indexdb_rna,
                "--ref", index_path,
                "--max_pos", "250",
                "-v"]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        aligned_basename = join(self.output_dir, "aligned")
        
        cmd = [self.sortmerna,
                "--ref", index_path,
                "--reads", self.set3,
                "--aligned", aligned_basename,
                "--id", "0.97",
                "--coverage", "0.97",
                "--log",
                "--otu_map",
                "--de_novo_otu",
                "--fastx",
                "-v",
                "-d", datadir,
                "--task", self.ALIGN_REPORT]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        try:
            proc = run(cmd, stdout=PIPE, stderr=PIPE)
            if proc.stderr: print(proc.stderr)
        except:
            msg = '{}: ERROR running sortmerna: {}'.format(FUNC, sys.exc_info()[0])
            print(msg)
        
        # Correct number of clusters in OTU-map
        with open(aligned_basename + ".log") as f_log:
            self.assertTrue("The input reads file or reference file is empty" in f_log.read())
            
        print("{}: Run time: {}".format(FUNC, time.time() - start))
    #END test_empty_query_file
           
    @unittest.skip("Skip until bug 54 fixed")
    def test_mate_pairs(self):
        """ Test outputting FASTQ files for merged
            mate pair reads.

            Conditions: input FASTQ file of mate paired reads:
            Total 10000 reads of which,
                1000 - align
                1000 - align
                2000 - random
                2000 - align
                2000 - align
                2000 - random

            Always only 6000 will align at any point, at the other 4000 are
            random reads.
            Using neither --paired_in or --paired_out, the --aligned file
            will have 6000 reads.
            With --paired_in, the --aligned file will contain 10000 reads
                              the --other file will contain 0 reads
            With --paired_out, the --aligned file will contain 2000 reads
                               the --other file will contain 8000 reads
        """
        FUNC = "test_mate_pairs"
        print(FUNC)
        start = time.time()
        
        index_db = join(self.output_dir, "db_bac16s")
        index_path = "%s,%s" % (self.db_bac16s, index_db)
        datadir = join(self.output_dir, 'kvdb')
        
        cmd = [self.indexdb_rna,
                "--ref", index_path,
                "--max_pos", "250",
                "-v"]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)
        
        aligned_basename = join(self.output_dir, "aligned")
        nonaligned_basename = join(self.output_dir, "nonaligned")
        
        # launch normally
        cmd = [self.sortmerna,
                "--ref", index_path,
                "--reads", self.set4,
                "--aligned", aligned_basename,
                "--other", nonaligned_basename,
                "--fastx",
                "--log",
                "-v",
                "-d", datadir,
                "--task", self.ALIGN_REPORT]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)
        
        f_log = open(aligned_basename + ".log")
        f_log_str = f_log.read()
        self.assertTrue("Total reads passing E-value threshold" in f_log_str)
        self.assertTrue("Total reads failing E-value threshold" in f_log_str)
        f_log.seek(0)
        for line in f_log:
            if line.startswith("    Total reads passing E-value threshold"):
                num_hits = (re.split('Total reads passing E-value threshold = | \(', line)[1]).strip()
            elif line.startswith("    Total reads failing E-value threshold"):
                num_fail = (re.split('Total reads failing E-value threshold = | \(', line)[1]).strip()
        f_log.close()
        # Correct number of reads mapped
        self.assertEqual("6000", num_hits)
        # Correct number of clusters recorded
        self.assertEqual("4000", num_fail)
        # Correct number of aligned reads
        with open(aligned_basename + ".fastq") as f_aligned:
            num_aligned_reads = sum(1 for line in f_aligned)
        self.assertEqual(6000, num_aligned_reads/4)
        # Correct number of non-aligned reads
        with open(nonaligned_basename + ".fastq") as f_nonaligned:
            num_nonaligned_reads = sum(1 for line in f_nonaligned)
        self.assertEqual(4000, num_nonaligned_reads/4)
        
        # Clean up before next call
        remove(aligned_basename + ".log")
        remove(aligned_basename + ".fastq")
        remove(nonaligned_basename + ".fastq")
        self.cleanData(datadir)
        
        # launch with option --paired_in
        cmd = [self.sortmerna,
                "--ref", index_path,
                "--reads", self.set4,
                "--aligned", aligned_basename,
                "--other", nonaligned_basename,
                "--paired_in",
                "--fastx",
                "--log",
                "-v",
                "-d", datadir,
                "--task", self.ONLY_REPORT]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)
        f_log = open(aligned_basename + ".log")
        f_log_str = f_log.read()
        
        self.assertTrue("Total reads passing E-value threshold" in f_log_str)
        self.assertTrue("Total reads failing E-value threshold" in f_log_str)
        
        f_log.seek(0)
        for line in f_log:
            if line.startswith("    Total reads passing E-value threshold"):
                num_hits = (re.split('Total reads passing E-value threshold = | \(', line)[1]).strip()
            elif line.startswith("    Total reads failing E-value threshold"):
                num_fail = (re.split('Total reads failing E-value threshold = | \(', line)[1]).strip()
                
        f_log.close()
        # Correct number of reads mapped
        self.assertEqual("6000", num_hits)
        # Correct number of clusters recorded
        self.assertEqual("4000", num_fail)
        # Correct number of aligned reads
        NUM_EXPECTED = 10000
        with open(aligned_basename + ".fastq") as f_aligned:
            num_aligned_reads = sum(1 for line in f_aligned)
            if num_aligned_reads/4 != NUM_EXPECTED:
                print(proc)
        self.assertEqual(NUM_EXPECTED, num_aligned_reads/4)
        # Correct number of non-aligned reads
        with open(nonaligned_basename + ".fastq") as f_nonaligned:
            num_nonaligned_reads = sum(1 for line in f_nonaligned)
        self.assertEqual(0, num_nonaligned_reads/4)
        
        # Clean up before next call
        remove(aligned_basename + ".log")
        remove(aligned_basename + ".fastq")
        remove(nonaligned_basename + ".fastq")
        self.cleanData(datadir)
        
        # launch with option --paired_out
        cmd = [self.sortmerna,
                "--ref", index_path,
                "--reads", self.set4,
                "--aligned", aligned_basename,
                "--other", nonaligned_basename,
                "--paired_out",
                "--fastx",
                "--log",
                "-v",
                "-d", datadir,
                "--task", self.ONLY_REPORT]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)
        f_log = open(aligned_basename + ".log")
        f_log_str = f_log.read()
        
        self.assertTrue("Total reads passing E-value threshold" in f_log_str)
        self.assertTrue("Total reads failing E-value threshold" in f_log_str)
        
        f_log.seek(0)
        for line in f_log:
            if line.startswith("    Total reads passing E-value threshold"):
                num_hits = (re.split('Total reads passing E-value threshold = | \(', line)[1]).strip()
            elif line.startswith("    Total reads failing E-value threshold"):
                num_fail = (re.split('Total reads failing E-value threshold = | \(', line)[1]).strip()
        
        f_log.close()
        # Correct number of reads mapped
        self.assertEqual("6000", num_hits)
        # Correct number of clusters recorded
        self.assertEqual("4000", num_fail)
        # Correct number of aligned reads
        with open(aligned_basename + ".fastq") as f_aligned:
            num_aligned_reads = sum(1 for line in f_aligned)
        self.assertEqual(2000, num_aligned_reads/4)
        # Correct number of non-aligned reads
        with open(nonaligned_basename + ".fastq") as f_nonaligned:
            num_nonaligned_reads = sum(1 for line in f_nonaligned)
        self.assertEqual(8000, num_nonaligned_reads/4)
            
        print("{}: Run time: {}".format(FUNC, time.time() - start))
    #END test_mate_pairs

    def test_output_all_alignments_f_rc(self):
        """ Test SortMeRNA's option '--num_alignments 0' which should
            search both forward and reverse-complement query for
            alignments
        """
        FUNC = "test_output_all_alignments_f_rc"
        print(FUNC)
        start = time.time()
        
        index_db = join(self.output_dir, "ref_GQ099317")
        index_path = "%s,%s" % (self.db_GQ099317, index_db)
        datadir = join(self.output_dir, 'kvdb')
        
        cmd = [self.indexdb_rna,
                "--ref", index_path,
                "-v"]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)

        aligned_basename = join(self.output_dir, "aligned")
        
        # num_alignments 0
        cmd = [self.sortmerna,
                "--ref", index_path,
                "--reads", self.read_GQ099317,
                "--aligned", aligned_basename,
                "--num_alignments", "0",
                "--sam",
                "-v",
                "-d", datadir,
                "--task", self.ALIGN_REPORT]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)
        
        sam_alignments_expected = [['GQ099317.1.1325_157_453_0:0:0_0:0:0_99/1',
                                    '0',
                                    'GQ099317.1.1325_157_453_0:0:0_0:0:0_99/1',
                                    '1',
                                    '255',
                                    '101M',
                                    '*',
                                    '0',
                                    '0',
                                    'GCTGGCACGGAGTTAGCCGGGGCTTATAAATGGTACCGTCATTGATTCTTCCCATTCTTTCGAAGTTTACATCCCGAGGGACTTCATCCTTCACGCGGCGT',
                                    '*',
                                    'AS:i:202',
                                    'NM:i:0'],
                                   ['GQ099317.1.1325_157_453_0:0:0_0:0:0_99/1',
                                    '16',
                                    'GQ099317.1.1325_157_453_0:0:0_0:0:0_99/1',
                                    '102',
                                    '255',
                                    '101M',
                                    '*',
                                    '0',
                                    '0',
                                    'ACGCCGCGTGAAGGATGAAGTCCCTCGGGATGTAAACTTCGAAAGAATGGGAAGAATCAATGACGGTACCATTTATAAGCCCCGGCTAACTCCGTGCCAGC',
                                    '*',
                                    'AS:i:202',
                                    'NM:i:0']]
        sam_alignments = []
        with open("%s.sam" % aligned_basename) as aligned_f:
            for line in aligned_f:
                if line.startswith('@'):
                    continue
                alignment = line.strip().split("\t")
                sam_alignments.append(alignment)
        self.assertEqual(len(sam_alignments_expected), len(sam_alignments))
        for alignment in sam_alignments_expected:
            self.assertTrue(alignment in sam_alignments)
            
        print("{}: Run time: {}".format(FUNC, time.time() - start))
    #END test_output_all_alignments_f_rc

    def test_cigar_lcs_1(self):
        """ Test the following case for alignment:
            beginning from align_ref_start = 0 and align_que_start = X, the read finishes
            before the end of the reference
                      ref |----------------|
           que |------------------------|
                            LIS |-----|
                          ^
                          align_que_start
        """
        FUNC = "test_cigar_lcs_1"
        print(FUNC)
        start = time.time()
        
        index_db = join(self.output_dir, "subject_str")
        index_path = "%s,%s" % (self.subject_str_fp, index_db)
        datadir = join(self.output_dir, 'kvdb')
        
        cmd = [self.indexdb_rna,
                "--ref", index_path,
                "-v"]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        aligned_basename = join(self.output_dir, "aligned")
        
        cmd = [self.sortmerna,
                "--ref", index_path,
                "--reads", self.query_str_fp,
                "--aligned", aligned_basename,
                "--sam",
                "--blast", "1 qstrand cigar",
                "-v",
                "-d", datadir,
                "--task", self.ALIGN_REPORT]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)
        
        expected_alignment = ["AB271211", "Unc49508", "93.5", "1430",
                              "64", "30", "58", "1487", "1", "1446", "0",
                              "2069", "+",
                              "57S57M2I12M2D4M2I29M1D11M2I3M2D11M1I7M1D13M5D4M3D9M2D3M7D1260M"]
        actual_alignment = []
        with open("%s.blast" % aligned_basename) as aligned_f:
            for line in aligned_f:
                actual_alignment = line.strip().split('\t')
        expected_alignment.sort()
        actual_alignment.sort()
        self.assertEqual(expected_alignment, actual_alignment)
            
        print("{}: Run time: {}".format(FUNC, time.time() - start))
    #END test_cigar_lcs_1

    def test_blast_format_0(self):
        """ Test BLAST-like pairwise format
        """
        FUNC = "test_blast_format_0"
        print(FUNC)
        start = time.time()
        
        index_db = join(self.output_dir, "subject_str")
        index_path = "%s,%s" % (self.subject_str_fp, index_db)
        datadir = join(self.output_dir, 'kvdb')
        
        cmd = [self.indexdb_rna,
                "--ref", index_path,
                "-v"]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)
            
        aligned_basename = join(self.output_dir, "aligned")
        
        cmd = [self.sortmerna,
                "--ref", index_path,
                "--reads", self.query_str_fp,
                "--aligned", aligned_basename,
                "--sam",
                "--blast", "0",
                "-v",
                "-d", datadir,
                "--task", self.ALIGN_REPORT]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)
        
        expected_alignment = """Sequence ID: Unc49508 count=1; cluster_weight=4; cluster=Unc49508; cluster_score=1.000000; cluster_center=True; 
Query ID: AB271211 1487 residues
Score: 2394 bits (2041) Expect: 0   strand: +

Target:        2    AGAGTTTGATCCTGGCTCAGGACGAACGCTGGCGGCGTGCTTAACACATGCAAGTC--AC    59
                    ||||||||||||||||||||||*|||||||||||||||||*|||||||||||||||  ||
Query:        59    AGAGTTTGATCCTGGCTCAGGATGAACGCTGGCGGCGTGCCTAACACATGCAAGTCGAAC    118

Target:       60    GGGGGCCCGCAAGGGT--AACCGGCGAACGGGTGCGTAACACGTGAGCAATCTGCCGTC-    116
                    |||***|**|  ||*|  *|**||||*|||||||*|||||*|||*|| |||||**|*|| 
Query:       119    GGGAATCTTC--GGATTCTAGTGGCGGACGGGTGAGTAACGCGTAAG-AATCTAACTTCA    175

Target:      117    -CACTGGGGGATAGCCG-GCCCAACGGCCGGGTAATACCGCATACGTTCCCTTGCCGGCA    174
                     *||  |||||*|*|*| |***||| |*|*|*|||||||     ||*|   *|||||**|
Query:       176    GGAC--GGGGACAACAGTGGGAAAC-GACTGCTAATACC-----CGAT---GTGCCGCGA    224

Target:      175    TCGGTGGGGGAGGAAACCTCCGGGGGTGGACGAGGAGCTCGCGGCCTATCAGCTAGTTGG    234
                      |||       |||||||****||***||*||||||||*|||*|**||*||||||||||
Query:       225    --GGT-------GAAACCTAATTGGCCTGAAGAGGAGCTTGCGTCTGATTAGCTAGTTGG    275

Target:      235    TGGGGTCACGGCCTACCAAGGCGATGACGGGTAGCTGGTCTGAGAGGATGGCCAGCCACA    294
                    ||||||*|**||||||||||||||*||***||||||||||||||||||||**||||||||
Query:       276    TGGGGTAAGAGCCTACCAAGGCGACGATCAGTAGCTGGTCTGAGAGGATGAGCAGCCACA    335

Target:      295    TTGGGACTGAGATACGGCCCAGACTCCTACGGGAGGCAGCAGTGGGGAATATTGCGCAAT    354
                    *|||||||||||*|||||||||||||||||||||||||||||||||||||*||*||||||
Query:       336    CTGGGACTGAGACACGGCCCAGACTCCTACGGGAGGCAGCAGTGGGGAATTTTCCGCAAT    395

Target:      355    GGCCGCAAGGCTGACGCAGCGACGCCGCGTGAGGGAGGAAGGTCTTTGGATTGTAAACCT    414
                    ||*||*|||*||||||*|||*|||||||||||||||||||||||||||||||||||||||
Query:       396    GGGCGAAAGCCTGACGGAGCAACGCCGCGTGAGGGAGGAAGGTCTTTGGATTGTAAACCT    455

Target:      415    CTTTTCTCAAGGAAGAAGTTCTGACGGTACTTGAGGAATCAGCCTCGGCTAACTCCGTGC    474
                    ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:       456    CTTTTCTCAAGGAAGAAGTTCTGACGGTACTTGAGGAATCAGCCTCGGCTAACTCCGTGC    515

Target:      475    CAGCAGCCGCGGTAATACGGGGGAGGCAAGCGTTATCCGGAATTATTGGGCGTAAAGCGT    534
                    ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:       516    CAGCAGCCGCGGTAATACGGGGGAGGCAAGCGTTATCCGGAATTATTGGGCGTAAAGCGT    575

Target:      535    CCGCAGGTGGTCAGCCAAGTCTGCCGTCAAATCAGGTTGCTTAACGACCTAAAGGCGGTG    594
                    ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:       576    CCGCAGGTGGTCAGCCAAGTCTGCCGTCAAATCAGGTTGCTTAACGACCTAAAGGCGGTG    635

Target:      595    GAAACTGGCAGACTAGAGAGCAGTAGGGGTAGCAGGAATTCCCAGTGTAGCGGTGAAATG    654
                    ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:       636    GAAACTGGCAGACTAGAGAGCAGTAGGGGTAGCAGGAATTCCCAGTGTAGCGGTGAAATG    695

Target:      655    CGTAGAGATTGGGAAGAACATCGGTGGCGAAAGCGTGCTACTGGGCTGTATCTGACACTC    714
                    ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:       696    CGTAGAGATTGGGAAGAACATCGGTGGCGAAAGCGTGCTACTGGGCTGTATCTGACACTC    755

Target:      715    AGGGACGAAAGCTAGGGGAGCGAAAGGGATTAGATACCCCTGTAGTCCTAGCCGTAAACG    774
                    ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:       756    AGGGACGAAAGCTAGGGGAGCGAAAGGGATTAGATACCCCTGTAGTCCTAGCCGTAAACG    815

Target:      775    ATGGATACTAGGCGTGGCTTGTATCGACCCGAGCCGTGCCGAAGCTAACGCGTTAAGTAT    834
                    ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:       816    ATGGATACTAGGCGTGGCTTGTATCGACCCGAGCCGTGCCGAAGCTAACGCGTTAAGTAT    875

Target:      835    CCCGCCTGGGGAGTACGCACGCAAGTGTGAAACTCAAAGGAATTGACGGGGGCCCGCACA    894
                    ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:       876    CCCGCCTGGGGAGTACGCACGCAAGTGTGAAACTCAAAGGAATTGACGGGGGCCCGCACA    935

Target:      895    AGCGGTGGAGTATGTGGTTTAATTCGATGCAACGCGAAGAACCTTACCAAGACTTGACAT    954
                    ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:       936    AGCGGTGGAGTATGTGGTTTAATTCGATGCAACGCGAAGAACCTTACCAAGACTTGACAT    995

Target:      955    GTCGCGAACCCTGGTGAAAGCTGGGGGTGCCTTCGGGAGCGCGAACACAGGTGGTGCATG    1014
                    ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:       996    GTCGCGAACCCTGGTGAAAGCTGGGGGTGCCTTCGGGAGCGCGAACACAGGTGGTGCATG    1055

Target:     1015    GCTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTCG    1074
                    ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:      1056    GCTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTCG    1115

Target:     1075    TTCTTAGTTGCCAGCATTAAGTTGGGGACTCTAAGGAGACTGCCGGTGACAAACCGGAGG    1134
                    ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:      1116    TTCTTAGTTGCCAGCATTAAGTTGGGGACTCTAAGGAGACTGCCGGTGACAAACCGGAGG    1175

Target:     1135    AAGGTGGGGATGACGTCAAGTCAGCATGCCCCTTACGTCTTGGGCGACACACGTACTACA    1194
                    ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:      1176    AAGGTGGGGATGACGTCAAGTCAGCATGCCCCTTACGTCTTGGGCGACACACGTACTACA    1235

Target:     1195    ATGGTCGGGACAAAGGGCAGCGAACTCGCGAGAGCCAGCGAATCCCAGCAAACCCGGCCT    1254
                    ||||||||||||||||||||||||||*|||||||||||||||||||||||||||||||||
Query:      1236    ATGGTCGGGACAAAGGGCAGCGAACTTGCGAGAGCCAGCGAATCCCAGCAAACCCGGCCT    1295

Target:     1255    CAGTTCAGATTGCAGGCTGCAACTCGCCTGCATGAAGGAGGAATCGCTAGTAATCGCCGG    1314
                    ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:      1296    CAGTTCAGATTGCAGGCTGCAACTCGCCTGCATGAAGGAGGAATCGCTAGTAATCGCCGG    1355

Target:     1315    TCAGCATACGGCGGTGAATTCGTTCCCGGGCCTTGTACACACCGCCCGTCACACCATGGA    1374
                    ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:      1356    TCAGCATACGGCGGTGAATTCGTTCCCGGGCCTTGTACACACCGCCCGTCACACCATGGA    1415

Target:     1375    AGCTGGTCACGCCCGAAGTCATTACCTCAACCGCAAGGAGGGGGATGCCTAAGGC    1429
                    |||||||||||||||||||||||||||||||||||||||||||||||||||||||
Query:      1416    AGCTGGTCACGCCCGAAGTCATTACCTCAACCGCAAGGAGGGGGATGCCTAAGGC    1470

        """
        with open("%s.blast" % aligned_basename) as aligned_f:
            actual_alignment = aligned_f.readlines()
        self.assertTrue(expected_alignment, actual_alignment)
            
        print("{}: Run time: {}".format(FUNC, time.time() - start))
    #END test_blast_format_0

    def test_blast_format_1(self):
        """ Test BLAST-like pairwise format -m8
        """
        FUNC = 'test_blast_format_1'
        print(FUNC)
        start = time.time()
        
        index_db = join(self.output_dir, "subject_str")
        index_path = "%s,%s" % (self.subject_str_fp, index_db)
        datadir = join(self.output_dir, 'kvdb')
        
        cmd = [self.indexdb_rna,
                "--ref", index_path,
                "-v"]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        aligned_basename = join(self.output_dir, "aligned")
        
        cmd = [self.sortmerna,
                "--ref", index_path,
                "--reads", self.query_str_fp,
                "--aligned", aligned_basename,
                "--sam",
                "--blast", "1",
                "-v",
                "-d", datadir,
                "--task", self.ALIGN_REPORT]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)
        
        expected_alignment = ["AB271211", "Unc49508", "93.5", "1430", "64", "30", "58", "1487", "1", "1446", "0", "2069"]
        #expected_alignment = ["AB271211", "Unc49508", "93.4", "1412", "64", "30", "59", "1470", "2", "1429", "0", "2039"] # issue 137
        actual_alignment = []
        with open("%s.blast" % aligned_basename) as aligned_f:
            for line in aligned_f:
                actual_alignment = line.strip().split('\t')
        expected_alignment.sort()
        actual_alignment.sort()
        self.assertEqual(expected_alignment, actual_alignment)
            
        print("{}: Run time: {}".format(FUNC, time.time() - start))
    #END test_blast_format_1

    def test_blast_format_0_other(self):
        """ Test BLAST-like pairwise format with option '0 qstrand'
        """
        FUNC = "test_blast_format_0_other"
        print(FUNC)
        start = time.time()
        
        index_db = join(self.output_dir, "subject_str")
        index_path = "%s,%s" % (self.subject_str_fp, index_db)
        datadir = join(self.output_dir, 'kvdb')
        
        cmd = [self.indexdb_rna,
                "--ref", index_path,
                "-v"]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        aligned_basename = join(self.output_dir, "aligned")
        
        cmd = [self.sortmerna,
                "--ref", index_path,
                "--reads", self.query_str_fp,
                "--aligned", aligned_basename,
                "--sam",
                "--blast", "0 qstrand",
                "-v",
                "-d", datadir,
                "--task", self.ALIGN_REPORT]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        self.assertTrue(proc.stderr)
        if 'Windows' in platform.platform():
            error_msg = """for human-readable format, --blast [STRING] can only contain a single field '0'"""
        else:
            error_msg = """\n  \x1b[0;31mERROR\x1b[0m: for human-readable format, --blast [STRING] can only contain a single field '0'.\n\n"""
        print("{}: Asserting [{}] in [{}]".format(FUNC, error_msg, proc.stderr))
        self.assertTrue(error_msg in proc.stderr.decode('utf-8'))
        #self.assertEqual(error_msg, proc.stderr.decode('utf-8'))
            
        print("{}: Run time: {}".format(FUNC, time.time() - start))
    #END test_blast_format_0_other

    def test_blast_format_1_other(self):
        """ Test BLAST-like -m8 tabular format with unsupported field
        """
        FUNC = "test_blast_format_1_other"
        print(FUNC)
        start = time.time()
        
        index_db = join(self.output_dir, "subject_str")
        index_path = "%s,%s" % (self.subject_str_fp, index_db)
        datadir = join(self.output_dir, 'kvdb')
        
        cmd = [self.indexdb_rna,
                "--ref", index_path,
                "-v"]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)
        if proc.stderr: print(proc.stderr)

        aligned_basename = join(self.output_dir, "aligned")
        
        cmd = [self.sortmerna,
                "--ref", index_path,
                "--reads", self.query_str_fp,
                "--aligned", aligned_basename,
                "--sam",
                "--blast", "1 sstrand",
                "-v",
                "-d", datadir,
                "--task", self.ALIGN_REPORT]
        
        print("{}: {}".format(FUNC, ' '.join(cmd)))
        
        proc = run(cmd, stdout=PIPE, stderr=PIPE)

        self.assertTrue(proc.stderr)
        if 'Windows' in platform.platform():
            error_msg = """\n  ERROR: `sstrand` is not supported in --blast [STRING].\n\n"""
        else:
            error_msg = """\n  \x1b[0;31mERROR\x1b[0m: `sstrand` is not supported in --blast [STRING].\n\n"""
        self.assertEqual(error_msg, proc.stderr.decode('utf-8'))
            
        print("{}: Run time: {}".format(FUNC, time.time() - start))
    #END test_blast_format_1_other
#END class SortmernaTests

#
# GLOBALS
#
subject_str = """>Unc49508 count=1; cluster_weight=4; cluster=Unc49508; cluster_score=1.000000; cluster_center=True; 
tagagtttgatcctggctcaggacgaacgctggcggcgtgcttaacacatgcaagtcacgggggcccgcaagggtaaccggcgaacgggtgcgta
acacgtgagcaatctgccgtccactgggggatagccggcccaacggccgggtaataccgcatacgttcccttgccggcatcggtgggggaggaaa
cctccgggggtggacgaggagctcgcggcctatcagctagttggtggggtcacggcctaccaaggcgatgacgggtagctggtctgagaggatgg
ccagccacattgggactgagatacggcccagactcctacgggaggcagcagtggggaatattgcgcaatggccgcaaggctgacgcagcgacgcc
gcgtgagggaggaaggtctttggattgtaaacctcttttctcaaggaagaagttctgacggtacttgaggaatcagcctcggctaactccgtgcc
agcagccgcggtaatacgggggaggcaagcgttatccggaattattgggcgtaaagcgtccgcaggtggtcagccaagtctgccgtcaaatcagg
ttgcttaacgacctaaaggcggtggaaactggcagactagagagcagtaggggtagcaggaattcccagtgtagcggtgaaatgcgtagagattg
ggaagaacatcggtggcgaaagcgtgctactgggctgtatctgacactcagggacgaaagctaggggagcgaaagggattagatacccctgtagt
cctagccgtaaacgatggatactaggcgtggcttgtatcgacccgagccgtgccgaagctaacgcgttaagtatcccgcctggggagtacgcacg
caagtgtgaaactcaaaggaattgacgggggcccgcacaagcggtggagtatgtggtttaattcgatgcaacgcgaagaaccttaccaagacttg
acatgtcgcgaaccctggtgaaagctgggggtgccttcgggagcgcgaacacaggtggtgcatggctgtcgtcagctcgtgtcgtgagatgttgg
gttaagtcccgcaacgagcgcaaccctcgttcttagttgccagcattaagttggggactctaaggagactgccggtgacaaaccggaggaaggtg
gggatgacgtcaagtcagcatgccccttacgtcttgggcgacacacgtactacaatggtcgggacaaagggcagcgaactcgcgagagccagcga
atcccagcaaacccggcctcagttcagattgcaggctgcaactcgcctgcatgaaggaggaatcgctagtaatcgccggtcagcatacggcggtg
aattcgttcccgggccttgtacacaccgcccgtcacaccatggaagctggtcacgcccgaagtcattacctcaaccgcaaggagggggatgccta
aggcagggctagtgactggggtgaagtcgtaacaaggtagccgt
"""

query_str = """>AB271211 1487 residues
TCCAACGCGTTGGGAGCTCTCCCATATGGTCGACCTGCAGGCGGCCGCACTAGTGATTAG
AGTTTGATCCTGGCTCAGGATGAACGCTGGCGGCGTGCCTAACACATGCAAGTCGAACGG
GAATCTTCGGATTCTAGTGGCGGACGGGTGAGTAACGCGTAAGAATCTAACTTCAGGACG
GGGACAACAGTGGGAAACGACTGCTAATACCCGATGTGCCGCGAGGTGAAACCTAATTGG
CCTGAAGAGGAGCTTGCGTCTGATTAGCTAGTTGGTGGGGTAAGAGCCTACCAAGGCGAC
GATCAGTAGCTGGTCTGAGAGGATGAGCAGCCACACTGGGACTGAGACACGGCCCAGACT
CCTACGGGAGGCAGCAGTGGGGAATTTTCCGCAATGGGCGAAAGCCTGACGGAGCAACGC
CGCGTGAGGGAGGAAGGTCTTTGGATTGTAAACCTCTTTTCTCAAGGAAGAAGTTCTGAC
GGTACTTGAGGAATCAGCCTCGGCTAACTCCGTGCCAGCAGCCGCGGTAATACGGGGGAG
GCAAGCGTTATCCGGAATTATTGGGCGTAAAGCGTCCGCAGGTGGTCAGCCAAGTCTGCC
GTCAAATCAGGTTGCTTAACGACCTAAAGGCGGTGGAAACTGGCAGACTAGAGAGCAGTA
GGGGTAGCAGGAATTCCCAGTGTAGCGGTGAAATGCGTAGAGATTGGGAAGAACATCGGT
GGCGAAAGCGTGCTACTGGGCTGTATCTGACACTCAGGGACGAAAGCTAGGGGAGCGAAA
GGGATTAGATACCCCTGTAGTCCTAGCCGTAAACGATGGATACTAGGCGTGGCTTGTATC
GACCCGAGCCGTGCCGAAGCTAACGCGTTAAGTATCCCGCCTGGGGAGTACGCACGCAAG
TGTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGTGGAGTATGTGGTTTAATTC
GATGCAACGCGAAGAACCTTACCAAGACTTGACATGTCGCGAACCCTGGTGAAAGCTGGG
GGTGCCTTCGGGAGCGCGAACACAGGTGGTGCATGGCTGTCGTCAGCTCGTGTCGTGAGA
TGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTCGTTCTTAGTTGCCAGCATTAAGTTGG
GGACTCTAAGGAGACTGCCGGTGACAAACCGGAGGAAGGTGGGGATGACGTCAAGTCAGC
ATGCCCCTTACGTCTTGGGCGACACACGTACTACAATGGTCGGGACAAAGGGCAGCGAAC
TTGCGAGAGCCAGCGAATCCCAGCAAACCCGGCCTCAGTTCAGATTGCAGGCTGCAACTC
GCCTGCATGAAGGAGGAATCGCTAGTAATCGCCGGTCAGCATACGGCGGTGAATTCGTTC
CCGGGCCTTGTACACACCGCCCGTCACACCATGGAAGCTGGTCACGCCCGAAGTCATTAC
CTCAACCGCAAGGAGGGGGATGCCTAAGGCAGGGCTAGTGACTGGGG
""" 

if __name__ == '__main__':
    unittest.main()
