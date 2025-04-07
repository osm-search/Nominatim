<?php
// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright

namespace Nominatim\API;

use Nominatim\API\SearchRequest;
use Nominatim\Database\SearchDatabase;
use Nominatim\Database\Place;
use Symfony\Component\Process\Process;
use Symfony\Component\Process\Exception\ProcessFailedException;

class Geocode
{
    protected $database;

    public function __construct(SearchDatabase $database)
    {
        $this->database = $database;
    }

    public function search(SearchRequest $aRequest)
    {
        $aPlace = $this->database->searchPlace($aRequest);

        // If original search returned no result and query looks like Japanese, try transliteration
        if (empty($aPlace)) {
            $query = $aRequest->getParam('q');

            // Check if the query contains any Japanese character (Kanji, Hiragana, Katakana)
            if (preg_match('/[\x{3040}-\x{30FF}\x{4E00}-\x{9FAF}]/u', $query)) {
                // Run Python script for transliteration
                $process = new Process(['python3', '/absolute/path/to/transliterator.py', $query]);
                try {
                    $process->mustRun();
                    $romaji = trim($process->getOutput());

                    // Log the transliteration attempt
                    error_log("Fallback to Romaji: $romaji");

                    // Update query and retry search
                    $aRequest->setParam('q', $romaji);
                    return $this->search($aRequest);
                } catch (ProcessFailedException $e) {
                    error_log("Transliteration failed: " . $e->getMessage());
                }
            }
        }

        return $aPlace;
    }
}

