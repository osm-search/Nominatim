
// The code in this file is released into the Public Domain.

#include <iostream>
#include <fstream>
#include <string>
#include <unordered_map>

#include <osmium/area/assembler.hpp>
#include <osmium/area/multipolygon_manager.hpp>

#include <osmium/geom/wkt.hpp>
#include <osmium/handler.hpp>
#include <osmium/handler/node_locations_for_ways.hpp>
#include <osmium/io/any_input.hpp>
#include <osmium/visitor.hpp>
#include <osmium/object_pointer_collection.hpp>
#include <osmium/index/map/sparse_mem_array.hpp>
#include <osmium/osm/object_comparisons.hpp>

typedef osmium::index::map::SparseMemArray<osmium::unsigned_object_id_type, osmium::Location> index_type;

typedef osmium::handler::NodeLocationsForWays<index_type, index_type> location_handler_type;

struct AbsoluteIdHandler : public osmium::handler::Handler {

    enum { BASE = 100000000 };

    void node(osmium::Node& o) {
        if (o.id() < 0)
            o.set_id(BASE-o.id());
    }

    void way(osmium::Way& o) {
        if (o.id() < 0)
            o.set_id(BASE-o.id());

        for (osmium::NodeRef &n: o.nodes())
            if (n.ref() < 0)
                n.set_ref(BASE-n.ref());
    }

    void relation(osmium::Relation& o) {
        if (o.id() < 0)
            o.set_id(BASE-o.id());

        for (auto &m : o.members())
            if (m.ref() < 0)
                m.set_ref(BASE-m.ref());
    }
};


class ExportToWKTHandler : public osmium::handler::Handler {

    osmium::geom::WKTFactory<> m_factory;
    std::unordered_map<std::string, std::ofstream>  m_files;

public:

    void node(const osmium::Node& node) {
        print_geometry(node.tags(), m_factory.create_point(node));
    }

    void way(const osmium::Way& way) {
        if (!way.nodes().empty()
            && (!way.is_closed() || !way.tags().get_value_by_key("area")))
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

    osmium::io::File input_file{argv[1]};

    // need to sort the data first and make ids absolute
    std::cerr << "Read file...\n";
    osmium::io::Reader reader{input_file};
    std::vector<osmium::memory::Buffer> changes;
    osmium::ObjectPointerCollection objects;
    AbsoluteIdHandler abshandler;
    while (osmium::memory::Buffer buffer = reader.read()) {
            osmium::apply(buffer, abshandler, objects);
            changes.push_back(std::move(buffer));
    }
    reader.close();

    std::cerr << "Sort file...\n";
    objects.sort(osmium::object_order_type_id_version());

    osmium::area::Assembler::config_type assembler_config;
    osmium::area::MultipolygonManager<osmium::area::Assembler> mp_manager{assembler_config};

    std::cerr << "Pass 1...\n";
    index_type index_pos;
    index_type index_neg;
    location_handler_type location_handler(index_pos, index_neg);
    ExportToWKTHandler export_handler;
    osmium::apply(objects.begin(), objects.end(), location_handler,
                  export_handler, mp_manager);
    mp_manager.prepare_for_lookup();
    std::cerr << "Pass 1 done\n";


    std::cerr << "Pass 2...\n";
    osmium::apply(objects.cbegin(), objects.cend(), mp_manager.handler([&export_handler](osmium::memory::Buffer&& buffer) {
        osmium::apply(buffer, export_handler);
    }));

    export_handler.close();
    std::cerr << "Pass 2 done\n";
}


