// Help page (#/help): how to get a GitHub token the generator can publish with.
export function Help({ repo, isDefaultRepo }) {
  return (
    <article className="help">
      <a className="help-back" href="#/">&larr; Back to the generator</a>
      <h2>How to get a GitHub token</h2>
      <p>
        The generator commits each site to a GitHub repo, adds a workflow that builds it, and turns
        on GitHub Pages. The token decides whether it is allowed to do that.
      </p>
      {isDefaultRepo ? (
        <p>
          The current repo, <strong>{repo}</strong>, uses the server's token (GITHUB_TOKEN on
          Render). To publish to your own repo, open the profile menu, change the repo and enter
          your own token.
        </p>
      ) : (
        <p>
          The current repo is <strong>{repo}</strong>. Enter a token that can write to it in the
          profile menu; it is used when you generate a site and is not stored.
        </p>
      )}

      <h3>Create or edit a token</h3>
      <ol>
        <li>
          Open{' '}
          <a href="https://github.com/settings/personal-access-tokens" target="_blank" rel="noreferrer">
            https://github.com/settings/personal-access-tokens
          </a>
          .
        </li>
        <li>
          <strong>Fine-grained token:</strong> select the repo and, under Repository permissions,
          set Contents, Workflows and Pages to Read and write. If Pages was never enabled on the
          repo, also set Administration to Read and write.
        </li>
        <li>
          <strong>Classic token:</strong> tick the repo and workflow scopes.
        </li>
        <li>Copy the token and paste it into the profile menu at the top right.</li>
      </ol>
      <p>
        Editing a fine-grained token's permissions keeps the same token value. If you create a new
        token for the server, update GITHUB_TOKEN on Render and redeploy.
      </p>

      <h3>If something fails</h3>
      <p>
        <strong>"Resource not accessible by personal access token"</strong> or{' '}
        <strong>"not built or published"</strong>: the token may not add the build workflow. Add the
        Workflows permission (or the workflow scope) and generate again. The site source is still
        saved to the repo.
      </p>
      <p>
        <strong>"Could not switch Pages to deploy from GitHub Actions"</strong> or{' '}
        <strong>"Could not enable Pages"</strong>: the token may not change the Pages setting.
        Either add the Pages permission above, or set it once by hand:
      </p>
      <ol>
        <li>
          Open{' '}
          <a href={`https://github.com/${repo}/settings/pages`} target="_blank" rel="noreferrer">
            Settings &gt; Pages
          </a>{' '}
          in the repo.
        </li>
        <li>Under Build and deployment &gt; Source, choose GitHub Actions.</li>
        <li>
          Open the{' '}
          <a href={`https://github.com/${repo}/actions`} target="_blank" rel="noreferrer">
            Actions
          </a>{' '}
          tab, pick the failed "Deploy generated site" run and click Re-run all jobs, or generate
          again.
        </li>
      </ol>
      <p>This is needed once per repo.</p>

      <h3>Emails</h3>
      <p>
        After each generation a summary (request, links and Claude cost) is emailed to the address
        you signed in with. Emails are sent by{' '}
        <a href="https://resend.com/" target="_blank" rel="noreferrer">https://resend.com/</a>. If
        none arrives, check your spam folder; the result on the main page also says whether the
        email was sent.
      </p>
    </article>
  )
}
