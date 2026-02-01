<script>
    import { onMount } from 'svelte';
    import { fade, fly } from 'svelte/transition';

    let entry = null;
    let loading = true;
    let rating = 0;
    let timeClass = null; // 'am', 'pm', 'ambiguous'
    let error = null;
    let stats = { total_entries: 0, voted_entries: 0, average_rating: 0 };
    let hasVotedRating = false;

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
        hasVotedRating = false;
        
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

    async function submitVote(isDeny = false) {
        if (!entry) return;
        
        if (isDeny) {
            // No validation needed for deny
        } else {
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
        
        fetchEntry();
        
        try {
            await fetch('/api/vote', {
                method: 'POST',
                body: JSON.stringify(voteData),
                headers: { 'Content-Type': 'application/json' }
            });
            fetchStats();
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

<style>
    :global(.marked) {
        font-weight: 900;
        text-decoration: underline;
        color: #000;
    }
</style>

<div class="min-h-screen bg-gray-100 flex flex-col items-center p-4">
    <!-- Sticky Stats Bar -->
    <div class="sticky top-0 z-50 w-full max-w-md mb-4 bg-white rounded-xl shadow-md p-4 border-b-2 border-blue-500">
        <div class="flex justify-between text-sm font-bold text-gray-700 mb-2">
            <span>Progress: {stats.voted_entries} / {stats.total_entries}</span>
            <span>{progress.toFixed(2)}%</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-3 mb-2">
            <div class="bg-blue-600 h-3 rounded-full transition-all duration-500" style="width: {progress}%"></div>
        </div>
        <div class="flex justify-between items-center text-xs text-gray-500">
            <span>Avg Rating: <span class="font-bold text-yellow-600">{stats.average_rating.toFixed(1)} ★</span></span>
            <span class="italic">0 ★ = Denied</span>
        </div>
    </div>

    <div class="relative w-full max-w-md flex-1 mb-20" style="min-height: 500px;">
        {#if loading}
            <div class="absolute inset-0 flex items-center justify-center bg-white rounded-xl shadow-xl">
                <p class="text-gray-500 animate-pulse">Finding next quote...</p>
            </div>
        {:else if error}
             <div class="absolute inset-0 flex flex-col items-center justify-center bg-white rounded-xl shadow-xl p-6 text-center">
                <p class="text-red-500 mb-4 font-bold">{error}</p>
                <button on:click={fetchEntry} class="px-6 py-2 bg-blue-500 text-white rounded-lg shadow">Retry</button>
            </div>
        {:else if entry}
            <div in:fade={{ duration: 200 }} out:fly={{ x: -200, duration: 300 }} class="absolute inset-0 bg-white rounded-xl shadow-2xl overflow-hidden flex flex-col">
                <!-- Card Header -->
                <div class="bg-gray-800 text-white p-4 text-center flex justify-between items-center">
                    <span class="text-2xl font-mono font-bold">
                        {entry.valid_times ? entry.valid_times[0] : '??:??'}
                    </span>
                    <a href={entry.link} target="_blank" class="text-xs text-blue-300 underline">View Source</a>
                </div>

                <!-- Content -->
                <div class="flex-1 p-6 overflow-y-auto flex flex-col">
                    <div class="text-center mb-6">
                        <p class="font-bold text-lg text-gray-900">{entry.title}</p>
                        {#if entry.author}<p class="text-gray-600 italic">by {entry.author}</p>{/if}

                        <!-- Categories -->
                        {#if entry.categories && entry.categories.length > 0}
                            <div class="flex flex-wrap gap-1 mt-2 justify-center">
                                {#each entry.categories as cat}
                                    <span class="px-2 py-0.5 bg-gray-200 text-gray-600 text-[10px] uppercase tracking-wider rounded-full">
                                        {cat}
                                    </span>
                                {/each}
                            </div>
                        {/if}
                    </div>

                    <div class="prose prose-lg text-gray-700 mb-6 italic text-center flex-1 flex flex-col justify-center">
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
                </div>

                <!-- Controls -->
                <div class="bg-gray-50 p-4 border-t border-gray-200 space-y-6">
                    
                    <!-- Time Classification -->
                    <div class="grid grid-cols-3 gap-2">
                        {#each ['am', 'pm', 'ambiguous'] as t}
                            <button 
                                class="py-3 px-1 text-xs font-bold rounded-lg uppercase border-2 transition-all
                                {timeClass === t 
                                    ? 'border-blue-600 bg-blue-600 text-white shadow-inner scale-95' 
                                    : 'border-gray-200 bg-white text-gray-400 hover:border-gray-300'}"
                                on:click={() => setTimeClass(t)}
                            >
                                {t}
                            </button>
                        {/each}
                    </div>

                    <!-- Star Rating (Full Row) -->
                    <div class="flex justify-between items-center bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
                        <span class="text-xs font-bold text-gray-400 uppercase">Rating:</span>
                        <div class="flex space-x-2">
                            {#each [1, 2, 3, 4, 5] as star}
                                <button 
                                    on:click={() => setRating(star)}
                                    class="text-3xl focus:outline-none transition-transform active:scale-150"
                                >
                                    <span class={star <= rating ? 'text-yellow-400' : 'text-gray-200'}>★</span>
                                </button>
                            {/each}
                        </div>
                    </div>

                    <!-- Action Row -->
                    <div class="flex gap-2">
                        <button 
                            on:click={() => submitVote(true)}
                            class="flex-1 py-4 rounded-xl font-bold text-red-500 border-2 border-red-100 hover:bg-red-50 transition-all uppercase text-sm"
                        >
                            Deny
                        </button>
                        
                        <button 
                            on:click={() => submitVote(false)}
                            disabled={!hasVotedRating || !timeClass}
                            class="flex-[2] py-4 rounded-xl font-bold text-white transition-all shadow-lg text-sm uppercase
                            {!hasVotedRating || !timeClass 
                                ? 'bg-gray-300 cursor-not-allowed shadow-none' 
                                : 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 transform active:scale-95'}"
                        >
                            Vote & Next
                        </button>
                    </div>
                </div>
            </div>
        {/if}
    </div>
</div>