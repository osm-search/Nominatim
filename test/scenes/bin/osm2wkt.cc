
// The code in this file is released into the Public Domain.

#include <iostream>
#include <fstream>
#include <string>
#include <unordered_map>

#include <osmium/area/assembler.hpp>
#include <osmium/area/multipolygon_collector.hpp>
#include <osmium/area/problem_reporter_exception.hpp>
#include <osmium/geom/wkt.hpp>
#include <osmium/handler.hpp>
#include <osmium/handler/node_locations_for_ways.hpp>
#include <osmium/io/any_input.hpp>
#include <osmium/visitor.hpp>
#include <osmium/index/map/sparse_mem_array.hpp>

typedef osmium::index::map::SparseMemArray<osmium::unsigned_object_id_type, osmium::Location> index_type;

typedef osmium::handler::NodeLocationsForWays<index_type, index_type> location_handler_type;


class ExportToWKTHandler : public osmium::handler::Handler {

    osmium::geom::WKTFactory<> m_factory;
    std::unordered_map<std::string, std::ofstream>  m_files;

public:

    void node(const osmium::Node& node) {
        print_geometry(node.tags(), m_factory.create_point(node));
    }

    void way(const osmium::Way& way) {
        if (!way.is_closed() || !way.tags().get_value_by_key("area"))
            print_geometry(way.tags(), m_factory.create_linestring(way));
    }

    void area(const osmium::Area& area) {
        if (!area.from_way() || area.tags().get_value_by_key("area"))
            print_geometry(area.tags(), m_factory.create_multipolygon(area));
    }

    void close() {
        for (auto& fd : m_files)
            fd.second.close();
    }

private:

    void print_geometry(const osmium::TagList& tags, const std::string& wkt) {
        const char* scenario = tags.get_value_by_key("test:section");
        const char* id = tags.get_value_by_key("test:id");
        if (scenario && id) {
            auto& fd = m_files[std::string(scenario)];
            if (!fd.is_open())
                fd.open(std::string(scenario) + ".wkt");
            fd << id << " |  " << wkt << "\n";
        }
    }

}; // class ExportToWKTHandler

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " OSMFILE\n";
        exit(1);
    }

    std::string input_filename {argv[1]};

    osmium::area::ProblemReporterException problem_reporter;
    osmium::area::Assembler::config_type assembler_config(&problem_reporter);
    osmium::area::MultipolygonCollector<osmium::area::Assembler> collector(assembler_config);

    std::cerr << "Pass 1...\n";
    osmium::io::Reader reader1(input_filename, osmium::osm_entity_bits::relation);
    collector.read_relations(reader1);
    std::cerr << "Pass 1 done\n";

    index_type index_pos;
    index_type index_neg;
    location_handler_type location_handler(index_pos, index_neg);

    std::cerr << "Pass 2...\n";
    ExportToWKTHandler export_handler;
    osmium::io::Reader reader2(input_filename);
    osmium::apply(reader2, location_handler, export_handler, collector.handler([&export_handler](osmium::memory::Buffer&& buffer) {
        osmium::apply(buffer, export_handler);
    }));
    reader2.close();
    export_handler.close();
    std::cerr << "Pass 2 done\n";
}


