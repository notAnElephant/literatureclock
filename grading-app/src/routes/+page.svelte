<script>
    import {onMount} from 'svelte';
    import {fade, fly} from 'svelte/transition';

    let entry = null;
    let loading = true;
    let rating = 0;
    let timeClass = null; // 'am', 'pm', 'ambiguous'
    let error = null;
    let stats = {total_entries: 0, voted_entries: 0, average_rating: 0};

    async function fetchStats() {
        try {
            const res = await fetch('/api/stats');
            if (res.ok) {
                stats = await res.json();
            }
        } catch (e) {
            console.error("Stats fetch failed", e);
        }
    }

    async function fetchEntry() {
        loading = true;
        entry = null;
        rating = 0;
        timeClass = null;
        error = null;

        try {
            const res = await fetch('/api/entries');
            if (res.ok) {
                const data = await res.json();
                if (data && !data.error) {
                    entry = data;
                } else {
                    error = data?.error || "No entry found";
                }
            } else {
                error = "Failed to fetch";
            }
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

        let hasVotedRating = false;

    

            async function submitVote(isDeny = false) {

    

                if (!entry) return;

    

                

    

                // Deny logic: bypass AM/PM check, default to ambiguous

    

                if (isDeny) {

    

                    // No validation needed for deny

    

                } else {

    

                    // Basic validation for normal votes

    

                    if (!timeClass) {

    

                        alert("Please select AM, PM, or Ambiguous");

    

                        return;

    

                    }

    

                    if (rating === 0) {

    

                        alert("Please rate the quote (1-5 stars) or use Deny");

    

                        return;

    

                    }

    

                }

    

                

    

                const finalRating = isDeny ? 0 : rating;

    

                const finalTimeClass = isDeny ? (timeClass || 'ambiguous') : timeClass;

    

        

    

                const voteData = { entry_id: entry.id, rating: finalRating, am_pm: finalTimeClass };

    

                

    

                // Animate out, fetch new, and update stats

    

                fetchEntry();

    

                hasVotedRating = false;

    

                if (isDeny) timeClass = null; // Reset timeClass only on deny (or keep it if you want persistence, but usually deny means clear)

    

                

    

                // Optimistically update stats locally or just fetch

    

                try {

    

                    await fetch('/api/vote', {

    

                        method: 'POST',

    

                        body: JSON.stringify(voteData),

    

                        headers: { 'Content-Type': 'application/json' }

    

                    });

    

                    fetchStats(); // Update stats from server

    

                } catch (e) {

    

                    console.error("Vote failed silently", e);

    

                }

    

            }

        

        function setTimeClass(val) {

            timeClass = val;

        }

        

        function setRating(val) {

            rating = val;

            hasVotedRating = true;

        }

    onMount(() => {
        fetchStats();
        fetchEntry();
    });

    $: progress = stats.total_entries > 0 ? (stats.voted_entries / stats.total_entries) * 100 : 0;
</script>

<div class="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
    <div class="w-full max-w-md mb-4 bg-white rounded-xl shadow p-4">
        <div class="flex justify-between text-sm text-gray-600 mb-2">
            <span>Progress: {stats.voted_entries} / {stats.total_entries}</span>
            <span>{progress.toFixed(2)}%</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2.5 mb-2">
            <div class="bg-blue-600 h-2.5 rounded-full" style="width: {progress}%"></div>
        </div>
        <div class="flex justify-between items-center text-xs text-gray-500 px-1">
            <span>Avg Rating: <span class="font-bold text-yellow-600">{stats.average_rating.toFixed(1)} ★</span></span>
            <span class="italic">0 = Denied</span>
        </div>
    </div>

    <h1 class="text-2xl font-bold mb-6 text-gray-800">Literature Clock Grader</h1>

    <div class="relative w-full max-w-md h-[600px]">
        {#if loading}
            <div class="absolute inset-0 flex items-center justify-center bg-white rounded-xl shadow-xl">
                <p class="text-gray-500 animate-pulse">Loading quote...</p>
            </div>
        {:else if error}
            <div class="absolute inset-0 flex flex-col items-center justify-center bg-white rounded-xl shadow-xl p-6 text-center">
                <p class="text-red-500 mb-4">{error}</p>
                <button on:click={fetchEntry} class="px-4 py-2 bg-blue-500 text-white rounded">Retry</button>
            </div>
        {:else if entry}
            <div in:fade={{ duration: 200 }} out:fly={{ x: -200, duration: 300 }}
                 class="absolute inset-0 bg-white rounded-xl shadow-2xl overflow-hidden flex flex-col">
                <!-- Card Header / Time -->
                <div class="bg-gray-800 text-white p-4 text-center">
                    <span class="text-3xl font-mono font-bold">
                        {entry.valid_times ? entry.valid_times[0] : '??:??'}
                    </span>
                </div>

                <!-- Content -->
                <div class="flex-1 p-6 overflow-y-auto flex flex-col justify-center">
                    <div class="prose prose-lg text-gray-700 mb-6 italic text-center">
                        {#if entry.snippet !== ''}
                            <div>
                                {@html entry.snippet}
                            </div>
                        {:else}
                            <div>
                                <p>No snippet available.</p>
                            </div>
                        {/if}
                    </div>
                    <div class="text-right text-sm text-gray-500 mt-auto">
                        <p class="font-bold">{entry.title}</p>
                        {#if entry.author}<p>{entry.author}</p>{/if}
                    </div>

                    <!-- Categories -->
                    {#if entry.categories && entry.categories.length > 0}
                        <div class="flex flex-wrap gap-1 mt-4 justify-center">
                            {#each entry.categories as cat}
                                <span class="px-2 py-0.5 bg-gray-200 text-gray-600 text-xs rounded-full">
                                    {cat}
                                </span>
                            {/each}
                        </div>
                    {/if}
                </div>

                <!-- Controls -->
                <div class="bg-gray-50 p-4 border-t border-gray-200 space-y-4">

                                <!-- Time Classification -->
                                <div class="grid grid-cols-3 gap-2">
                                    {#each ['am', 'pm', 'ambiguous'] as t}
                                        <button
                                                class="py-2 px-1 text-sm font-semibold rounded uppercase border-2 transition-colors
                                {timeClass === t 
                                    ? 'border-blue-500 bg-blue-50 text-blue-700' 
                                    : 'border-gray-200 text-gray-400 hover:border-gray-300'}"
                                                on:click={() => setTimeClass(t)}
                                        >
                                            {t}
                                        </button>
                                    {/each}
                                </div>

                                                    <!-- Star Rating -->
                                                    <div class="flex items-center justify-between gap-4">
                                                        <button 
                                                            on:click={() => submitVote(true)}
                                                            class="px-4 py-2 border-2 border-red-200 text-red-500 rounded-lg font-bold text-xs uppercase hover:bg-red-50 transition-colors"
                                                        >
                                                            Deny
                                                        </button>
                                                        
                                                        <div class="flex justify-center space-x-1">
                                                            {#each [1, 2, 3, 4, 5] as star}
                                                                <button 
                                                                    on:click={() => setRating(star)}
                                                                    class="text-2xl focus:outline-none transition-transform active:scale-125"
                                                                >
                                                                    <span class={star <= rating ? 'text-yellow-400' : 'text-gray-300'}>★</span>
                                                                </button>
                                                            {/each}
                                                        </div>
                                                    </div>
                                
                                                    <!-- Submit -->
                                                    <button 
                                                        on:click={() => submitVote(false)}
                                                        disabled={!hasVotedRating || !timeClass}
                                                        class="w-full py-3 rounded-lg font-bold text-white transition-all shadow-lg
                                                        {!hasVotedRating || !timeClass 
                                                            ? 'bg-gray-300 cursor-not-allowed' 
                                                            : 'bg-gradient-to-r from-pink-500 to-red-500 hover:from-pink-600 hover:to-red-600 transform hover:-translate-y-1'}"
                                                    >
                                                        Vote & Next
                                                    </button>                            </div>
                            </div>
                        {/if}
                    </div>
                </div>
