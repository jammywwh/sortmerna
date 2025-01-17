/**
* FILE: writer.cpp
* Created: Nov 26, 2017 Sun
* @copyright 2016-19 Clarity Genomics BVBA
*/
#include <iomanip>
#include <sstream>
#include <chrono>
#include <iostream>

#include "writer.hpp"


// write read alignment results to disk using e.g. RocksDB
void Writer::write()
{
	{
		std::stringstream ss;
		ss << STAMP << "Writer " << id << " thread " << std::this_thread::get_id() << " started" << std::endl;
		std::cout << ss.str();
	}

	auto t = std::chrono::high_resolution_clock::now();
	int numPopped = 0;
	for (;;) 
	{
		Read read = writeQueue.pop();
		if (read.isEmpty)
		{
			if (writeQueue.getPushers() == 0)
				break; // no more records in the queue and no pushers => stop processing

			if (!read.isValid) 
				continue;
		}
		++numPopped;
		//std::string matchResultsStr = read.matchesToJson();
		std::string readstr = read.toString();
		if (!opts.dbg_put_kvdb && readstr.size() > 0)
		{
			kvdb.put(std::to_string(read.id), readstr);
		}
	}

	std::chrono::duration<double> elapsed = std::chrono::high_resolution_clock::now() - t;

	{
		std::stringstream ss;
		ss << STAMP << std::setprecision(2) << std::fixed << id << " thread " << std::this_thread::get_id()
			<< " done. Elapsed time: " << elapsed.count() << " s Reads written: " << numPopped << std::endl;
		std::cout << ss.str();
	}
} // Writer::write