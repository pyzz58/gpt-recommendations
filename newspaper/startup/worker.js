// Sole external scheduler for the EXISTING newspaper production workflow.
// No news/PDF/SMTP code here. Configure GH_ACTIONS_TOKEN as a Cloudflare Secret.
const DISPATCH_URL =
  "https://api.github.com/repos/pyzz58/gpt-recommendations/actions/workflows/newspaper.yml/dispatches";
const EXPECTED_CRON = "1 16 * * *"; // UTC 16:01 = Beijing 00:01 next day.

export default {
  async scheduled(controller, env) {
    if (controller.cron !== EXPECTED_CRON) {
      throw new Error("Unexpected cron: refusing to launch newspaper");
    }
    if (!env.GH_ACTIONS_TOKEN) {
      throw new Error("Missing Cloudflare secret GH_ACTIONS_TOKEN");
    }
    const response = await fetch(DISPATCH_URL, {
      method: "POST",
      headers: {
        "Accept": "application/vnd.github+json",
        "Authorization": `Bearer ${env.GH_ACTIONS_TOKEN}`,
        "Content-Type": "application/json",
        "User-Agent": "newspaper-scheduler-cloudflare",
        "X-GitHub-Api-Version": "2022-11-28"
      },
      body: JSON.stringify({
        ref: "main",
        inputs: { dry_run: "false", preview_kind: "live" }
      })
    });
    if (response.status !== 200 && response.status !== 204) {
      // Never print credentials or a potentially sensitive response body.
      throw new Error(`NEWSPAPER_STARTUP_FAILED github_http=${response.status}`);
    }
    // The current GitHub API can return 200 with the created run details;
    // older API versions can return 204 with no body.
    let runId = "not_provided";
    if (response.status === 200) {
      const details = await response.json();
      if (details && details.workflow_run_id) {
        runId = String(details.workflow_run_id);
      }
    }
    // A successful dispatch is not evidence of PDF creation or QQ delivery.
    console.log(`NEWSPAPER_DISPATCH_ACCEPTED github_http=${response.status} run_id=${runId} event=workflow_dispatch`);
  }
};
