1. we have generated ticket-lookup application with openspec and you. Now we need to add the new functionality which should be implemented on new url. The functionality needs to do the following: the user is describing its
problem and the application should search through the same excel file and cathegorize the problem to which category the user should create the ticket.The column for the categorization is ISSUETYPE. Update the SPEC.md and add      
the new specifications in openspec folder as different folder   


2. add me on both pages links to each other in html                                                                                                                                                                                    


3. ❯ we need another functionality: which should be implemented on new url. The functionality needs to do the following: the user is describing its
   problem and the application should search through the same csv  file resources/issues_export.csv now the user describes the problem and then the system should take a look at the column ASSIGNEE  and to recommend to the user       
   someone who can solve its problem because in the ASIGNEE column is the preson which solved the problem described in the ticket.You should recommend 2-3 users, and to use 4-5 most relevant tickets. You should also create links     
   for that page on the existing pages and you should update all the specs 

4. the expert recommendation should use LLM for recommending the user so can you please fix this. it should use the same methoid for search as the ticket lookup and categorization features
5. ❯ we want to have an error displayed "LLM ranking was unavailable; showing the best keyword match." in the expert recommendation when LLM ranking was unavailable
