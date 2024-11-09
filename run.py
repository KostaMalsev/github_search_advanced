import requests
import time
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict
import os
from pathlib import Path

class GitHubIssuesFinder:
    def __init__(self, token: str):
        """
        Initialize with GitHub token for API authentication.
        
        Args:
            token (str): GitHub Personal Access Token
        """
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'
        self.rate_limit_remaining = None
        self.rate_limit_reset = None

    def _check_rate_limit(self):
        """Check and handle GitHub API rate limits."""
        if self.rate_limit_remaining and self.rate_limit_remaining < 10:
            wait_time = self.rate_limit_reset - time.time()
            if wait_time > 0:
                print(f"Rate limit approaching. Waiting {wait_time:.2f} seconds...")
                time.sleep(wait_time + 1)

    def _update_rate_limit(self, response):
        """Update rate limit information from API response."""
        self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
        self.rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))

    def get_top_repos(self, min_stars: int = 1000, language: str = None) -> List[Dict]:
        """
        Get top GitHub repositories based on stars.
        
        Args:
            min_stars (int): Minimum number of stars
            language (str): Programming language filter
        
        Returns:
            List[Dict]: List of repository information
        """
        repos = []
        page = 1
        
        while True:
            self._check_rate_limit()
            
            query = f"stars:>={min_stars}"
            if language:
                query += f" language:{language}"
            
            params = {
                'q': query,
                'sort': 'stars',
                'order': 'desc',
                'per_page': 100,
                'page': page
            }
            
            response = requests.get(
                f'{self.base_url}/search/repositories',
                headers=self.headers,
                params=params
            )
            
            self._update_rate_limit(response)
            
            if response.status_code != 200:
                print(f"Error fetching repos: {response.status_code}")
                break
                
            data = response.json()
            if not data['items']:
                break
                
            repos.extend([{
                'name': repo['full_name'],
                'stars': repo['stargazers_count'],
                'language': repo['language'],
                'url': repo['html_url']
            } for repo in data['items']])
            
            page += 1
            if page > 10:  # Limit to first 1000 repositories
                break
                
        return repos

    def get_beginner_issues(self, repo_name: str) -> List[Dict]:
        """
        Get beginner-friendly issues for a repository.
        
        Args:
            repo_name (str): Repository name in format 'owner/repo'
        
        Returns:
            List[Dict]: List of beginner-friendly issues
        """
        beginner_labels = [
            'good first issue',
            'good-first-issue',
            'beginner',
            'beginner-friendly',
            'easy',
            'starter',
            'help wanted',
            'easy fix'
        ]
        
        issues = []
        page = 1
        
        while True:
            self._check_rate_limit()
            
            params = {
                'state': 'open',
                'labels': ','.join(beginner_labels),
                'per_page': 100,
                'page': page
            }
            
            response = requests.get(
                f'{self.base_url}/repos/{repo_name}/issues',
                headers=self.headers,
                params=params
            )
            
            self._update_rate_limit(response)
            
            if response.status_code != 200:
                break
                
            data = response.json()
            if not data:
                break
                
            issues.extend([{
                'title': issue['title'],
                'url': issue['html_url'],
                'labels': [label['name'] for label in issue['labels']],
                'created_at': issue['created_at'],
                'comments': issue['comments']
            } for issue in data])
            
            page += 1
            
        return issues

    def save_results(self, results: List[Dict], filename: str):
        """
        Save results to CSV file.
        
        Args:
            results (List[Dict]): Results to save
            filename (str): Output filename
        """
        df = pd.DataFrame(results)
        df.to_csv(filename, index=False)
        print(f"Results saved to {filename}")

def main():
    # Get GitHub token from environment variable
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        raise ValueError("Please set GITHUB_TOKEN environment variable")
    
    # Initialize finder
    finder = GitHubIssuesFinder(github_token)
    
    # Get top repositories
    languages = ['python', 'javascript', 'java', 'go', 'rust']
    all_results = []
    
    for language in languages:
        print(f"\nFetching top {language} repositories...")
        repos = finder.get_top_repos(min_stars=5000, language=language)
        
        for repo in repos[:20]:  # Process top 20 repos per language
            print(f"Fetching issues for {repo['name']}...")
            issues = finder.get_beginner_issues(repo['name'])
            
            for issue in issues:
                all_results.append({
                    'repository': repo['name'],
                    'repo_stars': repo['stars'],
                    'repo_language': repo['language'],
                    'repo_url': repo['url'],
                    'issue_title': issue['title'],
                    'issue_url': issue['url'],
                    'issue_labels': ', '.join(issue['labels']),
                    'created_at': issue['created_at'],
                    'comments': issue['comments']
                })
    
    # Save results
    output_dir = Path('github_issues')
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    finder.save_results(all_results, output_dir / f'beginner_issues_{timestamp}.csv')

if __name__ == "__main__":
    main()
