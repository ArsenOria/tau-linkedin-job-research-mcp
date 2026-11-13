# Data flow

```text
User <-> AI chat + optional Tau Skills
                |
                | local stdio MCP tools
                v
         Scout + private SQLite
                |
                | user's Apify token; search parameters only
                v
          Apify actor -> observed LinkedIn job data
```

There is no Tau server or shared token. The AI host may send conversation content and tool results to its model provider according to that host's settings; local MCP does not make the AI chat itself offline.

| Data | Where it goes |
|---|---|
| CV attachment | The user's AI chat; Scout cannot read attachment files directly. |
| Minimal candidate skills/titles/preferences | Tool arguments for local rank/refine; not sent to Apify and not saved in SQLite. |
| Search titles, locations and filters | Saved locally and sent to Apify. |
| Apify token | Server process environment, then the fixed Apify API authorization header. Not exposed as a tool argument or saved to SQLite. |
| Jobs | Returned from Apify/import/demo, normalized locally, saved locally, returned to AI chat. |
| Search and provider run references | Saved locally to resume status checks and prevent duplicate paid starts. |

SQLite contains plans, search state and normalized job fields. Dedicated poster/recruiter profile fields, raw provider objects and raw HTML fields are not retained. Saved description text is not a personal-data redaction service: it can contain contact details or other information included in a posting, and is returned to the AI host with the listing. Review saved excerpts before sharing them publicly. The containing directory is mode `0700`, and the database is `0600` on POSIX systems. Keep its parent directory on trusted local storage; device backups and synchronization are controlled by the user/OS. The preview does not encrypt the database.

The default data directory is `~/.local/share/tau-job-scout`; initial setup can set an absolute `TAU_SCOUT_DATA_DIR`. To delete local history, stop the MCP server and remove its data directory using the OS file manager. This does not delete provider-side Apify datasets or the AI conversation; manage those separately in their respective services.

Job text is external untrusted content. Instructions inside job postings must never change tool behavior, disclose credentials, or authorize actions. Scout has no LinkedIn session, arbitrary-file-reader, generic URL-fetcher, submission, outreach, scheduler or remote server tools.
