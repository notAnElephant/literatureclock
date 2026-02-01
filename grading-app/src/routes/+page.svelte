<script>
    import { onMount } from 'svelte';
    import { fade, fly } from 'svelte/transition';

    let entry = null;
    let loading = true;
    let rating = 0;
    let timeClass = null; // 'am', 'pm', 'ambiguous'
    let error = null;

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

    async function submitVote() {
        if (!entry) return;
        
        // Basic validation
        if (!timeClass) {
            alert("Please select AM, PM, or Ambiguous");
            return;
        }
        if (rating === 0) {
            alert("Please rate the quote (1-5 stars)");
            return;
        }

        const voteData = { entry_id: entry.id, rating, am_pm: timeClass };
        
        // Animate out and fetch new
        fetchEntry();

        try {
            await fetch('/api/vote', {
                method: 'POST',
                body: JSON.stringify(voteData),
                headers: { 'Content-Type': 'application/json' }
            });
        } catch (e) {
            console.error("Vote failed silently", e);
        }
    }
    
    function setTimeClass(val) {
        timeClass = val;
    }
    
    function setRating(val) {
        rating = val;
    }

    onMount(fetchEntry);
</script>

<div class="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
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
            <div in:fade={{ duration: 200 }} out:fly={{ x: -200, duration: 300 }} class="absolute inset-0 bg-white rounded-xl shadow-2xl overflow-hidden flex flex-col">
                <!-- Card Header / Time -->
                <div class="bg-gray-800 text-white p-4 text-center">
                    <span class="text-3xl font-mono font-bold">
                        {entry.valid_times ? entry.valid_times[0] : '??:??'}
                    </span>
                </div>

                <!-- Content -->
                <div class="flex-1 p-6 overflow-y-auto flex flex-col justify-center">
                    <div class="prose prose-lg text-gray-700 mb-6 italic text-center">
                        {@html entry.snippet}
                    </div>
                    <div class="text-right text-sm text-gray-500 mt-auto">
                        <p class="font-bold">{entry.title}</p>
                        {#if entry.author}<p>{entry.author}</p>{/if}
                    </div>
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
                    <div class="flex justify-center space-x-2">
                        {#each [1, 2, 3, 4, 5] as star}
                            <button 
                                on:click={() => setRating(star)}
                                class="text-3xl focus:outline-none transition-transform active:scale-125"
                            >
                                <span class={star <= rating ? 'text-yellow-400' : 'text-gray-300'}>★</span>
                            </button>
                        {/each}
                    </div>

                    <!-- Submit -->
                    <button 
                        on:click={submitVote}
                        disabled={!rating || !timeClass}
                        class="w-full py-3 rounded-lg font-bold text-white transition-all shadow-lg
                        {!rating || !timeClass 
                            ? 'bg-gray-300 cursor-not-allowed' 
                            : 'bg-gradient-to-r from-pink-500 to-red-500 hover:from-pink-600 hover:to-red-600 transform hover:-translate-y-1'}"
                    >
                        Vote & Next
                    </button>
                </div>
            </div>
        {/if}
    </div>
</div>